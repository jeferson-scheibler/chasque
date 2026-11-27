from datetime import timedelta
from unittest import mock

from django.contrib.gis.geos import Point
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from contas.models import Usuario
from lugares.models import Lugar

from . import ia, intencoes
from .models import Intencao, Salvo

LEGENDA = "Pizza de fermentação natural no Forno da Praça, em Lajeado! Ambiente aconchegante, vale cada fatia."


class ClienteFalso:
    """Faz o papel do Gemini: devolve a leitura dada (ou levanta o erro) e guarda o que recebeu."""

    modelo = "falso-1"

    def __init__(self, leitura=None, erro=None):
        self.leitura = leitura or ia.Leitura(
            frase="A pizza de fermentação natural", tags=["aconchegante", "comida-caseira"],
            lugar_nome="Forno da Praça", lugar_cidade="Lajeado", confianca="alta",
        )
        self.erro = erro
        self.entradas = []

    def ler(self, entrada):
        self.entradas.append(entrada)
        if self.erro:
            raise self.erro
        return self.leitura


class Base(TestCase):
    def setUp(self):
        self.ana = Usuario.objects.create_user(email="ana@exemplo.com", password="x" * 12, nome="Ana",
                                               cidade_base="Lajeado", usar_ia=True)
        self.forno = Lugar.objects.create(nome="Forno da Praça", ponto=Point(-51.96, -29.46), fonte="osm",
                                          id_externo="node/1", cidade="Lajeado")

    def salvo(self, texto=LEGENDA, usuario=None, codigo="C9xYz12AbCd", **extra):
        return Salvo.objects.create(usuario=usuario or self.ana, url=f"https://www.instagram.com/reel/{codigo}/",
                                    tipo="reel", texto=texto, **extra)


class MarcarPendenteTests(Base):
    def test_sem_ia_ligada_nada_entra_na_fila(self):
        self.ana.usar_ia = False
        self.ana.save()
        self.assertIsNone(intencoes.marcar_pendente(self.salvo()))
        self.assertFalse(Intencao.objects.exists())

    def test_sem_texto_nada_entra_na_fila(self):
        self.assertIsNone(intencoes.marcar_pendente(self.salvo(texto="   ")))
        self.assertFalse(Intencao.objects.exists())

    def test_texto_novo_entra_como_pendente(self):
        intencao = intencoes.marcar_pendente(self.salvo())
        self.assertEqual(intencao.estado, Intencao.Estado.PENDENTE)
        self.assertEqual(len(intencao.hash_entrada), 64)

    def test_mesmo_texto_nao_volta_para_a_fila(self):
        salvo = self.salvo()
        intencoes.marcar_pendente(salvo)
        intencoes.processar(ClienteFalso())
        intencoes.marcar_pendente(salvo)
        self.assertEqual(Intencao.objects.get().estado, Intencao.Estado.PRONTA)

    def test_texto_mudou_volta_para_a_fila(self):
        salvo = self.salvo()
        intencoes.marcar_pendente(salvo)
        intencoes.processar(ClienteFalso())
        salvo.texto = "Outro texto, agora sobre o café colonial"
        salvo.save()
        self.assertEqual(intencoes.marcar_pendente(salvo).estado, Intencao.Estado.PENDENTE)

    def test_confirmada_pela_pessoa_nao_e_sobrescrita(self):
        salvo = self.salvo()
        intencao = intencoes.marcar_pendente(salvo)
        intencao.estado = Intencao.Estado.CONFIRMADA
        intencao.frase = "O que eu escrevi"
        intencao.save()
        salvo.texto = "Texto novo"
        salvo.save()
        intencoes.marcar_pendente(salvo)
        intencao.refresh_from_db()
        self.assertEqual((intencao.estado, intencao.frase), (Intencao.Estado.CONFIRMADA, "O que eu escrevi"))

    def test_marcar_todos_so_pega_salvos_com_texto(self):
        self.salvo(codigo="AAAAAAA")
        self.salvo(codigo="BBBBBBB", texto="")
        self.assertEqual(intencoes.marcar_todos(self.ana), 1)


class ProcessarTests(Base):
    def test_sem_cliente_nada_e_lido(self):
        intencoes.marcar_pendente(self.salvo())
        self.assertEqual(intencoes.processar(), 0)
        self.assertEqual(Intencao.objects.get().estado, Intencao.Estado.PENDENTE)

    def test_le_frase_motivos_e_lugar(self):
        intencoes.marcar_pendente(self.salvo())
        cliente = ClienteFalso()
        self.assertEqual(intencoes.processar(cliente), 1)

        intencao = Intencao.objects.get()
        self.assertEqual(intencao.estado, Intencao.Estado.PRONTA)
        self.assertEqual(intencao.frase, "A pizza de fermentação natural")
        self.assertEqual(sorted(intencao.tags.values_list("slug", flat=True)), ["aconchegante", "comida-caseira"])
        self.assertEqual(intencao.lugar_sugerido, self.forno)
        self.assertEqual((intencao.modelo, intencao.versao_prompt), ("falso-1", intencoes.VERSAO_PROMPT))
        self.assertIsNotNone(intencao.lida_em)

        entrada = cliente.entradas[0]
        self.assertEqual((entrada.tipo, entrada.texto, entrada.cidade_base), ("reel", LEGENDA, "Lajeado"))
        self.assertIn(("vista-bonita", "Vista bonita"), entrada.motivos)

    def test_o_que_vai_para_a_ia_nao_tem_email_nem_nome(self):
        intencoes.marcar_pendente(self.salvo())
        cliente = ClienteFalso()
        intencoes.processar(cliente)
        enviado = repr(cliente.entradas[0])
        self.assertNotIn("ana@exemplo.com", enviado)
        self.assertNotIn("'Ana'", enviado)

    def test_motivo_inventado_e_descartado_e_no_maximo_tres(self):
        intencoes.marcar_pendente(self.salvo())
        leitura = ia.Leitura(frase="Tudo", confianca="media",
                             tags=["inventado", "vinho", "vinho", "natureza", "arte", "doces", 7])
        intencoes.processar(ClienteFalso(leitura))
        self.assertEqual(sorted(Intencao.objects.get().tags.values_list("slug", flat=True)),
                         ["arte", "natureza", "vinho"])

    def test_confianca_baixa_nao_deixa_frase_nem_motivos(self):
        intencoes.marcar_pendente(self.salvo())
        leitura = ia.Leitura(frase="Chute", tags=["vinho"], lugar_nome="Forno da Praça", confianca="baixa")
        intencoes.processar(ClienteFalso(leitura))
        intencao = Intencao.objects.get()
        self.assertEqual((intencao.frase, intencao.tags.count()), ("", 0))
        self.assertEqual(intencao.lugar_sugerido, self.forno)

    def test_confianca_desconhecida_vira_baixa(self):
        intencoes.marcar_pendente(self.salvo())
        intencoes.processar(ClienteFalso(ia.Leitura(frase="Algo", confianca="certeza")))
        self.assertEqual(Intencao.objects.get().confianca, Intencao.Confianca.BAIXA)

    def test_frase_longa_e_cortada_e_espacos_limpos(self):
        intencoes.marcar_pendente(self.salvo())
        intencoes.processar(ClienteFalso(ia.Leitura(frase="  muito \n  " + "a" * 300, confianca="alta")))
        frase = Intencao.objects.get().frase
        self.assertEqual(len(frase), 120)
        self.assertTrue(frase.startswith("muito a"))

    def test_salvo_que_ja_tem_lugar_nao_recebe_sugestao(self):
        intencoes.marcar_pendente(self.salvo(lugar=self.forno))
        intencoes.processar(ClienteFalso())
        self.assertIsNone(Intencao.objects.get().lugar_sugerido)

    def test_lugar_so_e_sugerido_sem_duvida(self):
        Lugar.objects.create(nome="Forno da Praça", ponto=Point(-51.2, -30.0), fonte="osm",
                             id_externo="node/2", cidade="Porto Alegre")
        self.assertEqual(intencoes.encontrar_lugar("Forno da Praca", "lajeado"), self.forno)
        self.assertIsNone(intencoes.encontrar_lugar("Forno da Praça", ""))  # dois iguais, sem cidade
        self.assertIsNone(intencoes.encontrar_lugar("Fo", "Lajeado"))
        self.assertIsNone(intencoes.encontrar_lugar("Bar que não existe", "Lajeado"))

    def test_erro_tenta_de_novo_e_desiste_na_terceira(self):
        intencoes.marcar_pendente(self.salvo())
        cliente = ClienteFalso(erro=ia.ErroIA("timeout"))
        for esperado in (Intencao.Estado.PENDENTE, Intencao.Estado.PENDENTE, Intencao.Estado.FALHOU):
            intencoes.processar(cliente)
            self.assertEqual(Intencao.objects.get().estado, esperado)
        self.assertEqual(intencoes.processar(cliente), 0)
        self.assertEqual(len(cliente.entradas), 3)

    def test_quem_desligou_a_ia_sai_da_fila(self):
        intencoes.marcar_pendente(self.salvo())
        self.ana.usar_ia = False
        self.ana.save()
        cliente = ClienteFalso()
        self.assertEqual(intencoes.processar(cliente), 0)
        self.assertEqual(cliente.entradas, [])

    def test_limite_por_dia_nao_trava_a_fila_dos_outros(self):
        bia = Usuario.objects.create_user(email="bia@exemplo.com", password="x" * 12, nome="Bia", usar_ia=True)
        intencoes.marcar_pendente(self.salvo(codigo="AAAAAAA"))
        intencoes.marcar_pendente(self.salvo(codigo="BBBBBBB", usuario=bia))
        # Ana já leu o limite hoje
        antigos = [self.salvo(codigo=f"Z{i:06d}") for i in range(intencoes.LIMITE_DIA)]
        Intencao.objects.bulk_create(
            Intencao(salvo=s, estado=Intencao.Estado.PRONTA, lida_em=timezone.now()) for s in antigos
        )
        cliente = ClienteFalso()
        self.assertEqual(intencoes.processar(cliente), 1)
        self.assertEqual(Intencao.objects.get(salvo__usuario=bia).estado, Intencao.Estado.PRONTA)
        self.assertEqual(Intencao.objects.filter(salvo__usuario=self.ana, estado="pendente").count(), 1)

    def test_lote_respeita_o_limite(self):
        for i in range(3):
            intencoes.marcar_pendente(self.salvo(codigo=f"L{i:06d}"))
        self.assertEqual(intencoes.processar(ClienteFalso(), limite=2), 2)
        self.assertEqual(Intencao.objects.filter(estado="pendente").count(), 1)

    def test_leitura_de_ontem_nao_conta_no_limite(self):
        antigos = [self.salvo(codigo=f"Y{i:06d}") for i in range(intencoes.LIMITE_DIA)]
        Intencao.objects.bulk_create(
            Intencao(salvo=s, estado=Intencao.Estado.PRONTA, lida_em=timezone.now() - timedelta(days=1))
            for s in antigos
        )
        intencoes.marcar_pendente(self.salvo())
        self.assertEqual(intencoes.processar(ClienteFalso()), 1)

    def test_apagar_o_salvo_apaga_a_intencao(self):
        salvo = self.salvo()
        intencoes.marcar_pendente(salvo)
        salvo.delete()
        self.assertFalse(Intencao.objects.exists())


class ComandoTests(Base):
    def test_sem_ia_configurada_nao_le_nada(self):
        intencoes.marcar_pendente(self.salvo())
        call_command("ler_intencoes", stdout=mock.MagicMock())
        self.assertEqual(Intencao.objects.get().estado, Intencao.Estado.PENDENTE)

    def test_todos_poe_na_fila_e_le_com_o_cliente_configurado(self):
        self.salvo()
        cliente = ClienteFalso()
        with mock.patch.object(ia, "cliente_padrao", return_value=cliente):
            call_command("ler_intencoes", todos="ANA@exemplo.com", stdout=mock.MagicMock())
        self.assertEqual(Intencao.objects.get().estado, Intencao.Estado.PRONTA)


class ApiTests(APITestCase):
    reel = "https://www.instagram.com/reel/C9xYz12AbCd/"

    def setUp(self):
        cache.clear()
        self.ana = Usuario.objects.create_user(email="ana@exemplo.com", password="x" * 12, nome="Ana")
        self.client.force_authenticate(self.ana)

    def ligar_ia(self):
        r = self.client.patch("/api/me/", {"usar_ia": True}, format="json")
        self.assertTrue(r.data["usar_ia"])

    def test_ia_comeca_desligada(self):
        self.assertFalse(self.client.get("/api/me/").data["usar_ia"])
        self.client.post("/api/salvos/", {"text": f"{LEGENDA} {self.reel}"}, format="json")
        self.assertFalse(Intencao.objects.exists())

    def test_compartilhar_com_texto_entra_na_fila(self):
        self.ligar_ia()
        r = self.client.post("/api/salvos/", {"text": f"{LEGENDA} {self.reel}"}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(Intencao.objects.get(salvo_id=r.data["id"]).estado, Intencao.Estado.PENDENTE)

    def test_editar_o_texto_poe_na_fila(self):
        self.ligar_ia()
        r = self.client.post("/api/salvos/", {"text": self.reel}, format="json")
        self.assertFalse(Intencao.objects.exists())
        self.client.patch(f"/api/salvos/{r.data['id']}/", {"texto": "Quero ir pela vista do pôr do sol"},
                          format="json")
        self.assertEqual(Intencao.objects.get().estado, Intencao.Estado.PENDENTE)

    def test_editar_sem_mudar_o_texto_nao_mexe_na_fila(self):
        self.ligar_ia()
        r = self.client.post("/api/salvos/", {"text": self.reel}, format="json")
        self.client.patch(f"/api/salvos/{r.data['id']}/", {"lugar_id": None}, format="json")
        self.assertFalse(Intencao.objects.exists())
