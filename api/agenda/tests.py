from datetime import date, datetime, timedelta
from unittest import mock
from zoneinfo import ZoneInfo

from django.contrib.gis.geos import Point
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APITestCase

from contas.models import Usuario
from lugares.models import Cidade, Lugar
from registros.models import Registro
from salvos.intencoes import frases_por_lugar
from salvos.models import Intencao, Salvo

from . import ical, push
from .livres import dia_livre, dias_livres, fins_de_semana
from .models import Agenda, InscricaoPush, Parada, Roteiro
from .planejar import atualizar_roteiros, avisar_pendentes, mensagem, planejar
from .roteiros import criar, montar

FUSO = ZoneInfo("America/Sao_Paulo")
SEXTA = date(2026, 11, 27)
SABADO = date(2026, 11, 28)
DOMINGO = date(2026, 11, 29)

ICS = b"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//teste//PT
BEGIN:VEVENT
UID:1
DTSTART;TZID=America/Sao_Paulo:20261128T140000
DTEND;TZID=America/Sao_Paulo:20261128T160000
SUMMARY:Aniversario da tia
END:VEVENT
BEGIN:VEVENT
UID:2
DTSTART;VALUE=DATE:20261206
DTEND;VALUE=DATE:20261207
SUMMARY:Viagem
END:VEVENT
BEGIN:VEVENT
UID:3
DTSTART;TZID=America/Sao_Paulo:20261205T090000
DTEND;TZID=America/Sao_Paulo:20261205T120000
RRULE:FREQ=WEEKLY;BYDAY=SA;COUNT=2
SUMMARY:Aula
END:VEVENT
BEGIN:VEVENT
UID:4
DTSTART;TZID=America/Sao_Paulo:20261213T110000
DTEND;TZID=America/Sao_Paulo:20261213T120000
TRANSP:TRANSPARENT
SUMMARY:Lembrete
END:VEVENT
END:VCALENDAR
"""


class IcalTests(SimpleTestCase):
    def test_normalizar(self):
        self.assertEqual(ical.normalizar("webcal://p01-caldav.icloud.com/x.ics"), "https://p01-caldav.icloud.com/x.ics")
        for ruim in ["http://exemplo.com/a.ics", "ftp://x/a", "https://x:8443/a.ics", "https://eu:senha@x/a", "a.ics"]:
            with self.assertRaises(ical.AgendaInvalida, msg=ruim):
                ical.normalizar(ruim)

    def test_recusa_endereco_interno(self):
        for ip in ["127.0.0.1", "10.0.0.5", "169.254.169.254", "::1", "192.168.0.1"]:
            with mock.patch("socket.getaddrinfo", return_value=[(None, None, None, None, (ip, 443))]):
                with self.assertRaises(ical.AgendaInvalida, msg=ip):
                    ical.baixar("https://agenda.exemplo.com/x.ics")

    def test_ocupados_com_repeticao_dia_inteiro_e_livre(self):
        ocupados = ical.ocupados(ICS, SEXTA, date(2026, 12, 20))
        self.assertIn((datetime(2026, 11, 28, 14, tzinfo=FUSO), datetime(2026, 11, 28, 16, tzinfo=FUSO)), ocupados)
        self.assertIn((datetime(2026, 12, 6, tzinfo=FUSO), datetime(2026, 12, 7, tzinfo=FUSO)), ocupados)
        self.assertEqual(sum(1 for a, _ in ocupados if a.hour == 9), 2)  # a aula repete
        self.assertFalse(any(a.day == 13 for a, _ in ocupados))  # evento marcado como livre não conta

    def test_arquivo_quebrado(self):
        with self.assertRaises(ical.AgendaInvalida):
            ical.ocupados(b"BEGIN:VCALENDAR\nisso nao e agenda", SEXTA, SABADO)


class LivresTests(SimpleTestCase):
    def test_fins_de_semana(self):
        self.assertEqual(fins_de_semana(SEXTA, 2), [(SABADO, DOMINGO), (date(2026, 12, 5), date(2026, 12, 6))])
        # no sábado, sobra o domingo
        self.assertEqual(fins_de_semana(SABADO, 2)[0], (None, DOMINGO))

    def test_escolhe_um_dia_por_fim_de_semana(self):
        ocupados = ical.ocupados(ICS, SEXTA, date(2026, 12, 20))
        self.assertFalse(dia_livre(SABADO, ocupados))
        # 28/11 ocupado: vai o domingo. 05/12 tem aula até as 12h e 06/12 é viagem: fim de semana cheio.
        # 12/12 tem a aula repetida: vai o 13/12, que só tem um lembrete marcado como livre.
        self.assertEqual(dias_livres(SEXTA, ocupados), [DOMINGO, date(2026, 12, 13)])


class Base(TestCase):
    def setUp(self):
        cache.clear()
        self.ana = Usuario.objects.create_user(email="ana@exemplo.com", password="x" * 12, nome="Ana",
                                               cidade_base="Lajeado")
        Cidade.objects.create(nome="Lajeado", ponto=Point(-51.96, -29.46), id_externo="relation/1")

    def lugar(self, nome, lng, lat, categoria="tourism=attraction", horario="", cidade="Estrela", salvar=True):
        lugar = Lugar.objects.create(nome=nome, ponto=Point(lng, lat), fonte="osm", id_externo=f"node/{nome}",
                                     categoria=categoria, horario=horario, cidade=cidade)
        if salvar:
            Salvo.objects.create(usuario=self.ana, lugar=lugar, url=f"https://www.instagram.com/p/{nome[:8]}x/",
                                 tipo="post")
        return lugar


class RoteiroTests(Base):
    def test_ordem_do_dia_e_so_o_que_abre(self):
        self.lugar("Bar do Porto", -51.96, -29.50, "amenity=bar")
        self.lugar("Cafe Colonial", -51.95, -29.50, "amenity=cafe")
        self.lugar("Cascata", -51.97, -29.51)
        self.lugar("Museu Fechado", -51.96, -29.51, "tourism=museum", horario="Mo-Fr 09:00-17:00")
        self.lugar("Pousada", -51.96, -29.50, "tourism=guest_house")
        visitado = self.lugar("Cantina Visitada", -51.96, -29.50, "amenity=restaurant")
        Registro.objects.create(usuario=self.ana, lugar=visitado, nota=5)
        self.lugar("Longe Demais", -53.5, -30.5)

        paradas = montar(self.ana, SABADO)
        self.assertEqual([p["lugar"].nome for p in paradas], ["Cafe Colonial", "Cascata", "Bar do Porto"])
        self.assertEqual([p["momento"] for p in paradas], ["manha", "tarde", "noite"])
        self.assertTrue(all(p["salvo"] for p in paradas))

    def test_lugar_fechado_no_momento_muda_de_momento(self):
        self.lugar("Cafe da Tarde", -51.95, -29.50, "amenity=cafe", horario="Sa 14:00-18:00")
        self.lugar("Cascata", -51.97, -29.51)
        momentos = {p["lugar"].nome: p["momento"] for p in montar(self.ana, SABADO)}
        self.assertEqual(momentos["Cafe da Tarde"], "tarde")

    def test_sem_lugares_suficientes_nao_monta(self):
        self.lugar("Sozinho", -51.96, -29.50)
        self.assertEqual(montar(self.ana, SABADO), [])
        self.assertIsNone(criar(self.ana, SABADO))

    def test_viagem_e_cidade(self):
        self.lugar("Cafe", -51.95, -29.50, "amenity=cafe")
        self.lugar("Cascata", -51.97, -29.51)
        roteiro = criar(self.ana, SABADO)
        self.assertEqual((roteiro.cidade, roteiro.viagem), ("Estrela", True))
        titulo, corpo = mensagem(roteiro)
        self.assertEqual(titulo, "Bate e volta para Estrela?")
        self.assertIn("Sábado livre na agenda", corpo)
        self.assertIn("Cafe e Cascata", corpo)

    def intencao(self, lugar, frase, estado="pronta"):
        salvo = Salvo.objects.filter(usuario=self.ana, lugar=lugar).first()
        return Intencao.objects.create(salvo=salvo, frase=frase, estado=estado)

    def test_aviso_lembra_o_motivo_de_ter_salvo(self):
        self.lugar("Cafe", -51.95, -29.50, "amenity=cafe")
        cascata = self.lugar("Cascata", -51.97, -29.51)
        self.intencao(cascata, "Banho de cachoeira gelada!")
        titulo, corpo = mensagem(criar(self.ana, SABADO))
        self.assertEqual(titulo, "Bate e volta para Estrela?")
        self.assertEqual(corpo, "Sábado livre na agenda. O roteiro passa por Cascata: Banho de cachoeira gelada. "
                                "Mais 1 parada perto.")

    def test_aviso_ignora_motivo_pendente_vazio_ou_de_outra_pessoa(self):
        cafe = self.lugar("Cafe", -51.95, -29.50, "amenity=cafe")
        cascata = self.lugar("Cascata", -51.97, -29.51)
        self.intencao(cafe, "Café", estado="pendente")
        self.intencao(cascata, "", estado="confirmada")
        bia = Usuario.objects.create_user(email="bia@exemplo.com", password="x" * 12, nome="Bia")
        alheio = Salvo.objects.create(usuario=bia, lugar=cafe, url="https://www.instagram.com/p/bia1/", tipo="post")
        Intencao.objects.create(salvo=alheio, frase="O café da Bia", estado="confirmada")
        self.assertIn("Cafe e Cascata", mensagem(criar(self.ana, SABADO))[1])

    def test_frase_do_link_mais_recente(self):
        cafe = self.lugar("Cafe", -51.95, -29.50, "amenity=cafe")
        self.intencao(cafe, "Motivo antigo")
        novo = Salvo.objects.create(usuario=self.ana, lugar=cafe, url="https://www.instagram.com/p/novo1/", tipo="post")
        Intencao.objects.create(salvo=novo, frase="Motivo novo", estado="confirmada")
        self.assertEqual(frases_por_lugar(self.ana.id, [cafe.id]), {cafe.id: "Motivo novo"})

    def test_parada_na_cidade_da_pessoa_nao_e_viagem(self):
        self.lugar("Cafe", -51.95, -29.50, "amenity=cafe", cidade="Lajeado")
        self.lugar("Cascata", -51.97, -29.51)
        self.lugar("Mirante", -51.97, -29.52, "tourism=viewpoint")
        roteiro = criar(self.ana, SABADO)
        self.assertEqual((roteiro.cidade, roteiro.viagem), ("Lajeado", False))
        self.assertEqual(mensagem(roteiro)[0], "Aproveite o fim de semana")

    def test_o_proximo_fim_de_semana_nao_repete(self):
        for i in range(4):
            self.lugar(f"Perto {i}", -51.96 + i * 0.01, -29.50, categoria="tourism=attraction")
        for i in range(4):
            self.lugar(f"Serra {i}", -50.87 + i * 0.01, -29.37, categoria="tourism=attraction")
        primeiro = {p.lugar.nome[:5] for p in criar(self.ana, SABADO).paradas.all()}
        segundo = {p.lugar.nome[:5] for p in criar(self.ana, date(2026, 12, 5)).paradas.all()}
        self.assertNotEqual(primeiro, segundo)

    def test_atualizar_tira_dia_ocupado_e_respeita_agora_nao(self):
        self.lugar("Cafe", -51.95, -29.50, "amenity=cafe")
        self.lugar("Cascata", -51.97, -29.51)
        atualizar_roteiros(self.ana, [SABADO.isoformat(), DOMINGO.isoformat()], SEXTA)
        self.assertEqual(Roteiro.objects.count(), 2)
        Roteiro.objects.filter(dia=DOMINGO).update(dispensado_em=datetime(2026, 11, 27, tzinfo=FUSO))
        atualizar_roteiros(self.ana, [DOMINGO.isoformat()], SEXTA)
        self.assertEqual([(r.dia, r.dispensado_em is not None) for r in Roteiro.objects.all()], [(DOMINGO, True)])


@override_settings(VAPID_PUBLICA="pub", VAPID_PRIVADA="priv")
class AvisoTests(Base):
    def setUp(self):
        super().setUp()
        self.lugar("Cafe", -51.95, -29.50, "amenity=cafe")
        self.lugar("Cascata", -51.97, -29.51)
        self.roteiro = criar(self.ana, SABADO)
        InscricaoPush.objects.create(usuario=self.ana, endpoint="https://fcm.googleapis.com/fcm/send/abc",
                                     p256dh="k", auth="a")

    def test_avisa_uma_vez_e_so_de_dia(self):
        with mock.patch("agenda.push.webpush") as enviar:
            self.assertEqual(avisar_pendentes(datetime(2026, 11, 26, 3, tzinfo=FUSO)), 0)  # madrugada
            self.assertEqual(avisar_pendentes(datetime(2026, 11, 24, 10, tzinfo=FUSO)), 0)  # cedo demais
            self.assertEqual(avisar_pendentes(datetime(2026, 11, 26, 10, tzinfo=FUSO)), 1)
            self.assertEqual(avisar_pendentes(datetime(2026, 11, 26, 11, tzinfo=FUSO)), 0)
        self.assertEqual(enviar.call_count, 1)
        self.assertIn("/abas/sugestoes/roteiro/", enviar.call_args.kwargs["data"])

    def test_inscricao_cancelada_some(self):
        resposta = mock.Mock(status_code=410)
        with mock.patch("agenda.push.webpush", side_effect=push.WebPushException("x", response=resposta)):
            self.assertEqual(push.enviar(self.ana, "t", "c", "/"), 0)
        self.assertFalse(InscricaoPush.objects.exists())

    def test_sem_aparelho_tenta_de_novo_depois(self):
        InscricaoPush.objects.all().delete()
        avisar_pendentes(datetime(2026, 11, 26, 10, tzinfo=FUSO))
        self.roteiro.refresh_from_db()
        self.assertIsNone(self.roteiro.notificado_em)

    def test_endpoint_valido(self):
        self.assertTrue(push.endpoint_valido("https://web.push.apple.com/QGx"))
        self.assertTrue(push.endpoint_valido("https://updates.push.services.mozilla.com/wpush/v2/x"))
        for ruim in ["http://fcm.googleapis.com/x", "https://fcm.googleapis.com.golpe.net/x", "https://127.0.0.1/x",
                     "https://fcm.googleapis.com:8443/x"]:
            self.assertFalse(push.endpoint_valido(ruim), ruim)


class ApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.ana = Usuario.objects.create_user(email="ana@exemplo.com", password="x" * 12, nome="Ana")
        self.bia = Usuario.objects.create_user(email="bia@exemplo.com", password="x" * 12, nome="Bia")
        self.client.force_authenticate(self.ana)
        for nome, cat in [("Cafe", "amenity=cafe"), ("Cascata", "tourism=attraction")]:
            lugar = Lugar.objects.create(nome=nome, ponto=Point(-51.96, -29.50), fonte="osm", id_externo=f"n/{nome}",
                                         categoria=cat)
            Salvo.objects.create(usuario=self.ana, lugar=lugar, url=f"https://www.instagram.com/p/{nome}xx/", tipo="post")

    def ligar(self, url="webcal://calendar.google.com/calendar/ical/x/private-abc/basic.ics", dados=ICS):
        with mock.patch("agenda.ical.baixar", return_value=dados), \
                mock.patch("agenda.planejar.timezone.localdate", return_value=SEXTA):
            return self.client.put("/api/agenda/", {"url": url}, format="json")

    def test_ligar_agenda_nao_devolve_o_endereco(self):
        r = self.ligar()
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["servico"], "calendar.google.com")
        self.assertNotIn("private-abc", str(r.data))
        self.assertEqual(r.data["dias_livres"][0], DOMINGO.isoformat())
        self.assertEqual(Agenda.objects.get().url, "https://calendar.google.com/calendar/ical/x/private-abc/basic.ics")
        self.assertTrue(Roteiro.objects.filter(usuario=self.ana, dia=DOMINGO).exists())
        self.assertNotIn("private-abc", str(self.client.get("/api/agenda/").data))

    def test_endereco_que_nao_abre_nao_troca_o_que_funcionava(self):
        self.ligar()
        with mock.patch("agenda.ical.baixar", side_effect=ical.AgendaInvalida("A agenda não abriu.")):
            r = self.client.put("/api/agenda/", {"url": "https://outra.exemplo.com/a.ics"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data["url"], ["A agenda não abriu."])
        self.assertEqual(Agenda.objects.get().servico, "calendar.google.com")

    def test_parada_traz_o_motivo_de_ter_salvo(self):
        salvo = Salvo.objects.get(usuario=self.ana, lugar__nome="Cascata")
        Intencao.objects.create(salvo=salvo, frase="Banho de cachoeira", estado="confirmada")
        self.ligar()
        with mock.patch("agenda.views.timezone.localdate", return_value=SEXTA):
            paradas = self.client.get("/api/roteiros/").data[0]["paradas"]
        self.assertEqual({p["lugar"]["nome"]: p["intencao"] for p in paradas}, {"Cafe": "", "Cascata": "Banho de cachoeira"})

    def test_roteiros_sao_de_cada_um(self):
        self.ligar()
        with mock.patch("agenda.views.timezone.localdate", return_value=SEXTA):
            lista = self.client.get("/api/roteiros/").data
            self.assertEqual([r["dia"] for r in lista], ["2026-11-29", "2026-12-13"])
            roteiro = lista[0]
            self.assertFalse(roteiro["visto"])
            self.assertEqual(len(roteiro["paradas"]), 2)
            self.assertIsNotNone(roteiro["paradas"][0]["salvo_id"])
            self.assertEqual([p["intencao"] for p in roteiro["paradas"]], ["", ""])
            self.assertTrue(self.client.get(f"/api/roteiros/{roteiro['id']}/").data["visto"])

            self.client.force_authenticate(self.bia)
            self.assertEqual(self.client.get("/api/roteiros/").data, [])
            self.assertEqual(self.client.get(f"/api/roteiros/{roteiro['id']}/").status_code, 404)
            self.assertEqual(self.client.delete(f"/api/roteiros/{roteiro['id']}/").status_code, 404)

            self.client.force_authenticate(self.ana)
            self.assertEqual(self.client.delete(f"/api/roteiros/{roteiro['id']}/").status_code, 204)
            self.assertEqual(len(self.client.get("/api/roteiros/").data), 1)

    def test_desligar_agenda(self):
        self.ligar()
        self.assertEqual(self.client.delete("/api/agenda/").status_code, 204)
        self.assertEqual(self.client.get("/api/agenda/").data, {"conectada": False})
        self.assertFalse(Roteiro.objects.filter(dia__gt=SEXTA).exists())

    def test_inscricao_push(self):
        r = self.client.post("/api/avisos/", {"endpoint": "https://127.0.0.1/x", "p256dh": "k", "auth": "a"},
                             format="json")
        self.assertEqual(r.status_code, 400)
        dados = {"endpoint": "https://fcm.googleapis.com/fcm/send/abc", "p256dh": "k", "auth": "a"}
        self.assertEqual(self.client.post("/api/avisos/", dados, format="json").status_code, 201)
        self.client.force_authenticate(self.bia)
        self.client.post("/api/avisos/", dados, format="json")  # o aparelho trocou de conta
        self.assertEqual(InscricaoPush.objects.get().usuario, self.bia)
        self.client.force_authenticate(self.ana)
        self.assertEqual(self.client.get("/api/avisos/").data["aparelhos"], 0)

    def test_planejar_le_agenda_atrasada(self):
        self.ligar()
        Agenda.objects.update(lida_em=datetime(2026, 11, 26, tzinfo=FUSO))
        with mock.patch("agenda.ical.baixar", return_value=ICS) as baixar:
            planejar(agora=datetime(2026, 11, 27, 3, tzinfo=FUSO))
        baixar.assert_called_once()

    def test_exportar_inclui_agenda(self):
        self.ligar()
        dados = self.client.get("/api/me/exportar/").data
        self.assertIn("private-abc", dados["agenda"]["url"])
        self.assertTrue(dados["roteiros"])
