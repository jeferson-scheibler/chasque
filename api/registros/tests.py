import datetime

from django.contrib.gis.geos import Point
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APITestCase

from contas.models import Usuario
from lugares.models import Lugar
from salvos.models import Salvo

from .models import PesoGosto, Registro


class Base(APITestCase):
    url = "/api/registros/"

    def setUp(self):
        cache.clear()
        self.ana = Usuario.objects.create_user(email="ana@exemplo.com", password="x" * 12, nome="Ana")
        self.bia = Usuario.objects.create_user(email="bia@exemplo.com", password="x" * 12, nome="Bia")
        self.client.force_authenticate(self.ana)
        self.cafe = Lugar.objects.create(nome="Café da Praça", ponto=Point(-51.96, -29.46), fonte="osm",
                                         id_externo="node/1", cidade="Lajeado", categoria="amenity=cafe")
        self.cascata = Lugar.objects.create(nome="Cascata do Moinho", ponto=Point(-51.8, -29.2), fonte="osm",
                                            id_externo="node/2", cidade="Encantado")

    def registrar(self, **dados):
        corpo = {"lugar_id": self.cafe.id, "nota": 5, "ocasiao": "casal", "tags": ["cafe-colonial", "silencioso"]}
        corpo.update(dados)
        return self.client.post(self.url, corpo, format="json")

    def pesos(self, ocasiao=""):
        return {p.tag.slug: p.peso for p in PesoGosto.objects.filter(usuario=self.ana, ocasiao=ocasiao)}


class RegistrarTests(Base):
    def test_registra_visita_com_motivos(self):
        r = self.registrar(motivo="Cuca de banana quentinha")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["lugar"]["nome"], "Café da Praça")
        self.assertEqual(sorted(r.data["tags"]), ["cafe-colonial", "silencioso"])
        self.assertEqual(r.data["visitado_em"], timezone.localdate().isoformat())
        self.assertTrue(Registro.objects.get().privado)

    def test_exige_pelo_menos_um_motivo(self):
        r = self.registrar(tags=[], motivo="")
        self.assertEqual(r.status_code, 400)
        self.assertIn("tags", r.data)
        # só o texto também vale
        self.assertEqual(self.registrar(tags=[], motivo="Atendimento da dona Ilse").status_code, 201)

    def test_recusa_data_no_futuro_e_nota_fora_da_escala(self):
        amanha = timezone.localdate() + datetime.timedelta(days=1)
        self.assertEqual(self.registrar(visitado_em=amanha.isoformat()).status_code, 400)
        self.assertEqual(self.registrar(nota=6).status_code, 400)
        self.assertEqual(self.registrar(ocasiao="festa").status_code, 400)
        self.assertEqual(self.registrar(tags=["nao-existe"]).status_code, 400)

    def test_exige_login(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.registrar().status_code, 401)


class ListaTests(Base):
    def test_lista_so_as_proprias_visitas_mais_recentes_primeiro(self):
        self.registrar(visitado_em="2026-01-10")
        self.registrar(lugar_id=self.cascata.id, tags=["natureza"], visitado_em="2026-03-02")
        self.client.force_authenticate(self.bia)
        self.registrar(tags=["animado"])
        self.client.force_authenticate(self.ana)
        nomes = [r["lugar"]["nome"] for r in self.client.get(self.url).data["results"]]
        self.assertEqual(nomes, ["Cascata do Moinho", "Café da Praça"])

    def test_busca_por_motivo_sem_acento_lugar_e_cidade(self):
        self.registrar()
        self.registrar(lugar_id=self.cascata.id, tags=["natureza"], motivo="Água geladíssima")
        buscar = lambda q: [r["lugar"]["nome"] for r in self.client.get(self.url, {"q": q}).data["results"]]
        self.assertEqual(buscar("cafe colonial"), ["Café da Praça"])
        self.assertEqual(buscar("agua gelad"), ["Cascata do Moinho"])
        self.assertEqual(buscar("encantado"), ["Cascata do Moinho"])
        self.assertEqual(buscar("silencio"), ["Café da Praça"])

    def test_nao_ve_nem_altera_visita_de_outra_pessoa(self):
        rid = self.registrar().data["id"]
        self.client.force_authenticate(self.bia)
        self.assertEqual(self.client.get(f"{self.url}{rid}/").status_code, 404)
        self.assertEqual(self.client.patch(f"{self.url}{rid}/", {"nota": 1}, format="json").status_code, 404)
        self.assertEqual(self.client.delete(f"{self.url}{rid}/").status_code, 404)


class PerfilTests(Base):
    def test_perfil_soma_pela_nota_no_geral_e_na_ocasiao(self):
        self.registrar(nota=5, tags=["cafe-colonial", "silencioso"], ocasiao="casal")
        self.registrar(lugar_id=self.cascata.id, nota=4, tags=["silencioso"], ocasiao="familia")
        self.assertEqual(self.pesos(), {"cafe-colonial": 1.0, "silencioso": 1.5})
        self.assertEqual(self.pesos("casal"), {"cafe-colonial": 1.0, "silencioso": 1.0})
        self.assertEqual(self.pesos("familia"), {"silencioso": 0.5})

    def test_nota_baixa_pesa_contra_e_editar_ou_apagar_recalcula(self):
        rid = self.registrar(nota=1, tags=["animado"]).data["id"]
        self.assertEqual(self.pesos(), {"animado": -1.0})
        self.client.patch(f"{self.url}{rid}/", {"nota": 3}, format="json")
        self.assertEqual(self.pesos(), {})  # nota 3 é neutra
        self.client.patch(f"{self.url}{rid}/", {"nota": 5}, format="json")
        self.assertEqual(self.pesos(), {"animado": 1.0})
        self.client.delete(f"{self.url}{rid}/")
        self.assertEqual(self.pesos(), {})

    def test_editar_sem_mandar_motivos_mantem_os_atuais(self):
        rid = self.registrar().data["id"]
        r = self.client.patch(f"{self.url}{rid}/", {"ocasiao": "amigos"}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(sorted(r.data["tags"]), ["cafe-colonial", "silencioso"])


class IntegracaoTests(Base):
    def test_salvo_mostra_que_o_lugar_ja_foi_visitado(self):
        salvo = Salvo.objects.create(usuario=self.ana, lugar=self.cafe, url="https://www.instagram.com/p/ABCDEF1/",
                                     tipo="post")
        self.assertFalse(self.client.get(f"/api/salvos/{salvo.id}/").data["visitado"])
        self.registrar()
        self.assertTrue(self.client.get(f"/api/salvos/{salvo.id}/").data["visitado"])
        self.assertTrue(self.client.get("/api/salvos/").data["results"][0]["visitado"])

    def test_motivos_disponiveis(self):
        r = self.client.get("/api/tags/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data), 27)
        cafe = next(t for t in r.data if t["slug"] == "cafe-colonial")
        self.assertEqual((cafe["nome"], cafe["grupo_nome"]), ("Café colonial", "Comida e bebida"))

    def test_exportar_e_excluir_conta_levam_as_visitas(self):
        self.registrar(motivo="Cuca")
        exportado = self.client.get("/api/me/exportar/").data
        self.assertEqual(exportado["registros"][0]["motivo"], "Cuca")
        self.assertTrue(exportado["perfil_de_gosto"])
        self.client.delete("/api/me/", {"senha": "x" * 12}, format="json")
        self.assertFalse(Registro.objects.filter(usuario__email="ana@exemplo.com").exists())


class SugestoesTests(Base):
    url_sug = "/api/sugestoes/"

    def setUp(self):
        super().setUp()
        from lugares.models import Cidade, Tag

        self.lajeado = Cidade.objects.create(nome="Lajeado", ponto=Point(-51.9617, -29.4669), id_externo="node/9")
        self.tag = {t.slug: t for t in Tag.objects.all()}
        # o café da Base (já tem lugar próprio) recebe motivos para a Ana visitar
        self.cafe.tags.set([self.tag["cafe-colonial"], self.tag["silencioso"]])
        self.colonial_perto = self.lugar("Casa da Cuca", -51.965, -29.468, ["cafe-colonial", "silencioso"])
        self.colonial_longe = self.lugar("Cuca da Serra", -51.78, -29.36, ["cafe-colonial", "silencioso"])  # uns 20 km
        self.bar_perto = self.lugar("Bar do Centro", -51.962, -29.467, ["animado", "musica-ao-vivo"])
        self.sem_tag = self.lugar("Loja Qualquer", -51.961, -29.466, [])

    def lugar(self, nome, lng, lat, slugs):
        lugar = Lugar.objects.create(nome=nome, ponto=Point(lng, lat), fonte="osm", id_externo=f"node/{nome}",
                                     cidade="Lajeado")
        lugar.tags.set([self.tag[s] for s in slugs])
        return lugar

    def sugerir(self, **params):
        params.setdefault("lat", -29.4669)
        params.setdefault("lng", -51.9617)
        return self.client.get(self.url_sug, params)

    def nomes(self, r):
        return [s["lugar"]["nome"] for s in r.data["resultados"]]

    def test_sem_gosto_nao_sugere_e_avisa(self):
        r = self.sugerir()
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.data["tem_gosto"])
        self.assertEqual(r.data["resultados"], [])

    def test_visita_ensina_e_o_perto_vem_antes_do_longe(self):
        self.registrar(nota=5, tags=["cafe-colonial", "silencioso"])
        r = self.sugerir()
        self.assertTrue(r.data["tem_gosto"])
        self.assertEqual(self.nomes(r), ["Casa da Cuca", "Cuca da Serra"])
        self.assertEqual(r.data["resultados"][0]["combina"], ["cafe-colonial", "silencioso"])
        self.assertIsNotNone(r.data["resultados"][0]["lugar"]["distancia_m"])

    def test_lugar_visitado_e_lugar_que_desagradou_ficam_de_fora(self):
        self.registrar(nota=5, tags=["cafe-colonial"])
        self.registrar(lugar_id=self.cascata.id, nota=1, tags=["animado"])
        nomes = self.nomes(self.sugerir())
        self.assertNotIn("Café da Praça", nomes)  # já visitado
        self.assertNotIn("Bar do Centro", nomes)  # animado pesou contra
        self.assertNotIn("Loja Qualquer", nomes)  # nenhum motivo em comum

    def quando(self, **params):
        self.client.put("/api/me/preferencias/", {"tags": ["animado"]}, format="json")
        return self.sugerir(**params)

    def test_lugar_fechado_no_dia_sai_e_o_aberto_mostra_o_horario(self):
        self.bar_perto.horario = "Tu-Su 18:00-23:00"  # fecha às segundas
        self.bar_perto.save()
        aberto = self.lugar("Bar Aberto", -51.9625, -29.4672, ["animado"])
        aberto.horario = "Mo-Su 11:00-23:00"
        aberto.save()
        r = self.quando(quando="2026-11-30")  # segunda-feira
        self.assertEqual(self.nomes(r), ["Bar Aberto"])
        self.assertEqual(r.data["resultados"][0]["horario"], {"estado": "aberto", "texto": "11:00 às 23:00"})
        self.assertIn("Bar do Centro", self.nomes(self.quando(quando="2026-12-01")))  # terça ele abre

    def test_hora_filtra_dentro_do_dia(self):
        self.bar_perto.horario = "Mo-Su 18:00-23:00"
        self.bar_perto.save()
        self.assertEqual(self.nomes(self.quando(quando="2026-11-30", hora="20:00")), ["Bar do Centro"])
        self.assertEqual(self.nomes(self.quando(quando="2026-11-30", hora="10:00")), [])

    def test_sem_horario_fica_na_lista_avisando_e_visita_no_mesmo_dia_da_semana_vira_prova(self):
        import datetime

        r = self.quando(quando="2026-11-30")
        self.assertEqual(self.nomes(r), ["Bar do Centro"])
        self.assertEqual(r.data["resultados"][0]["horario"], {"estado": "sem_info", "texto": ""})
        # a Bia foi ao bar numa segunda (23/11/2026): abre às segundas
        Registro.objects.create(usuario=self.bia, lugar=self.bar_perto, nota=4, ocasiao="amigos",
                                visitado_em=datetime.date(2026, 11, 23))
        horario = self.quando(quando="2026-11-30").data["resultados"][0]["horario"]
        self.assertEqual(horario, {"estado": "visto", "texto": "", "visitas": 1})
        # numa quarta não há prova
        self.assertEqual(self.quando(quando="2026-12-02").data["resultados"][0]["horario"]["estado"], "sem_info")

    def test_confirmado_vem_antes_de_sem_horario_de_igual_gosto(self):
        confirmado = self.lugar("Bar Confirmado", -51.9621, -29.4668, ["animado", "musica-ao-vivo"])
        confirmado.horario = "Mo-Su 11:00-23:00"
        confirmado.save()
        r = self.quando(quando="2026-11-30")
        self.assertEqual(self.nomes(r)[0], "Bar Confirmado")

    def test_sem_quando_nao_traz_horario_e_data_ruim_da_erro(self):
        self.assertIsNone(self.quando().data["resultados"][0]["horario"])
        self.assertEqual(self.sugerir(quando="amanhã").status_code, 400)
        self.assertEqual(self.sugerir(hora="20:00").status_code, 400)  # hora sozinha, sem data

    def test_preferencias_declaradas_dao_sugestao_antes_da_primeira_visita(self):
        r = self.client.put("/api/me/preferencias/", {"tags": ["musica-ao-vivo"]}, format="json")
        self.assertEqual(r.data, {"tags": ["musica-ao-vivo"]})
        r = self.sugerir()
        self.assertTrue(r.data["tem_gosto"])
        self.assertEqual(self.nomes(r), ["Bar do Centro"])

    def test_ocasiao_usa_o_gosto_daquela_ocasiao(self):
        self.registrar(lugar_id=self.cascata.id, nota=5, tags=["animado"], ocasiao="amigos")
        self.registrar(nota=5, tags=["silencioso"], ocasiao="casal")
        casal = self.nomes(self.sugerir(ocasiao="casal"))
        amigos = self.nomes(self.sugerir(ocasiao="amigos"))
        self.assertEqual(casal[0], "Casa da Cuca")
        self.assertEqual(amigos[0], "Bar do Centro")
        self.assertEqual(self.sugerir(ocasiao="festa").status_code, 400)

    def test_salvo_ganha_destaque(self):
        self.client.put("/api/me/preferencias/", {"tags": ["silencioso"]}, format="json")
        Salvo.objects.create(usuario=self.ana, lugar=self.colonial_longe, url="https://www.instagram.com/p/XYZ123/",
                             tipo="post")
        r = self.sugerir()
        salvo = next(s for s in r.data["resultados"] if s["lugar"]["nome"] == "Cuca da Serra")
        self.assertTrue(salvo["salvo"])

    def test_origem_cai_na_cidade_da_pessoa_e_depois_na_ultima_visita(self):
        self.client.put("/api/me/preferencias/", {"tags": ["silencioso"]}, format="json")
        r = self.client.get(self.url_sug)
        self.assertIsNone(r.data["origem"])  # sem posição, sem cidade, sem visita
        self.ana.cidade_base = "lajeado"
        self.ana.save()
        r = self.client.get(self.url_sug)
        self.assertEqual((r.data["origem"]["tipo"], r.data["origem"]["nome"]), ("cidade", "Lajeado"))
        self.assertTrue(r.data["resultados"])
        r = self.client.get(self.url_sug, {"cidade_id": self.lajeado.id})
        self.assertEqual(r.data["origem"]["cidade_id"], self.lajeado.id)

    def test_gosto_de_outra_pessoa_nao_entra(self):
        self.client.force_authenticate(self.bia)
        self.registrar(nota=5, tags=["cafe-colonial", "silencioso"])
        self.client.force_authenticate(self.ana)
        self.assertEqual(self.sugerir().data["resultados"], [])

    def test_motivo_raro_vale_mais_que_motivo_comum(self):
        # "natureza" em muitos lugares, "cerveja-artesanal" em um só
        for i in range(12):
            self.lugar(f"Praça {i}", -51.9615 - i * 0.0004, -29.4665, ["natureza"])
        cervejaria = self.lugar("Cervejaria do Vale", -51.990, -29.480, ["cerveja-artesanal"])
        self.client.put("/api/me/preferencias/", {"tags": ["natureza", "cerveja-artesanal"]}, format="json")
        nomes = self.nomes(self.sugerir())
        self.assertEqual(nomes[0], cervejaria.nome)  # mais longe, mas mais específica

    def test_topo_tem_variedade_de_categorias(self):
        for i in range(6):
            lugar = self.lugar(f"Parque {i}", -51.9616 - i * 0.0003, -29.4668, ["natureza"])
            lugar.categoria = "leisure=park"
            lugar.save()
        mirante = self.lugar("Mirante", -51.93, -29.45, ["natureza"])
        mirante.categoria = "tourism=viewpoint"
        mirante.save()
        self.client.put("/api/me/preferencias/", {"tags": ["natureza"]}, format="json")
        nomes = self.nomes(self.sugerir())
        self.assertIn("Mirante", nomes[:3])  # sem a regra, os 6 parques viriam antes


class MapaTests(Base):
    def test_lugares_salvos_e_visitados_sem_repetir(self):
        Salvo.objects.create(usuario=self.ana, lugar=self.cafe, url="https://www.instagram.com/p/AAAAA1/", tipo="post")
        Salvo.objects.create(usuario=self.ana, lugar=self.cascata, url="https://www.instagram.com/p/AAAAA2/", tipo="post")
        Salvo.objects.create(usuario=self.ana, url="https://www.instagram.com/p/AAAAA3/", tipo="post")  # sem lugar
        self.registrar(nota=4, visitado_em="2026-01-01")
        ultima = self.registrar(nota=5).data["id"]
        self.client.force_authenticate(self.bia)
        self.registrar(lugar_id=self.cascata.id, tags=["natureza"])
        self.client.force_authenticate(self.ana)

        r = self.client.get("/api/mapa/")
        self.assertEqual(r.data["type"], "FeatureCollection")
        por_nome = {f["properties"]["nome"]: f for f in r.data["features"]}
        self.assertEqual(set(por_nome), {"Café da Praça", "Cascata do Moinho"})
        cafe = por_nome["Café da Praça"]["properties"]
        self.assertEqual((cafe["tipo"], cafe["visitas"], cafe["nota"], cafe["visita_id"]), ("visitado", 2, 5, ultima))
        self.assertEqual(por_nome["Cascata do Moinho"]["properties"]["tipo"], "salvo")  # a visita da Bia não conta
        self.assertEqual(por_nome["Café da Praça"]["geometry"]["coordinates"], [-51.96, -29.46])


class ComunidadeTests(Base):
    """Motivos da comunidade: soma anônima de visitas boas, a partir de 3 pessoas."""

    def setUp(self):
        super().setUp()
        self.pessoas = [self.ana, self.bia] + [
            Usuario.objects.create_user(email=f"p{i}@exemplo.com", password="x" * 12, nome=f"P{i}") for i in range(3)
        ]

    def visita(self, pessoa, lugar=None, nota=5, tags=("cafe-colonial",)):
        self.client.force_authenticate(pessoa)
        r = self.registrar(lugar_id=(lugar or self.cafe).id, nota=nota, tags=list(tags))
        self.client.force_authenticate(self.ana)
        return r.data["id"]

    def motivos(self, lugar=None):
        r = self.client.get(f"/api/lugares/{(lugar or self.cafe).id}/")
        return {m["slug"]: m["pessoas"] for m in r.data["motivos_comunidade"]}

    def test_so_aparece_a_partir_de_tres_pessoas(self):
        self.visita(self.pessoas[0])
        self.visita(self.pessoas[1])
        self.assertEqual(self.motivos(), {})
        self.visita(self.pessoas[2])
        self.assertEqual(self.motivos(), {"cafe-colonial": 3})

    def test_mesma_pessoa_varias_vezes_conta_uma(self):
        for _ in range(3):
            self.visita(self.pessoas[0])
        self.assertEqual(self.motivos(), {})

    def test_visita_ruim_nao_conta(self):
        for p in self.pessoas[:2]:
            self.visita(p)
        self.visita(self.pessoas[2], nota=2)  # "o que não funcionou?"
        self.assertEqual(self.motivos(), {})

    def test_api_mostra_so_a_contagem(self):
        for p in self.pessoas[:3]:
            self.visita(p)
        corpo = self.client.get(f"/api/lugares/{self.cafe.id}/").content.decode()
        for p in self.pessoas:
            self.assertNotIn(p.email, corpo)
            self.assertNotIn(p.nome, corpo.replace("Café da Praça", ""))

    def test_apagar_visita_ou_conta_tira_da_soma(self):
        ids = [self.visita(p) for p in self.pessoas[:3]]
        self.client.force_authenticate(self.pessoas[2])
        self.client.delete(f"{self.url}{ids[2]}/")
        self.assertEqual(self.motivos(), {})
        self.visita(self.pessoas[2])
        self.visita(self.pessoas[3])
        self.assertEqual(self.motivos(), {"cafe-colonial": 4})
        self.client.force_authenticate(self.pessoas[3])
        self.client.delete("/api/me/", {"senha": "x" * 12}, format="json")
        self.client.force_authenticate(self.ana)
        self.assertEqual(self.motivos(), {"cafe-colonial": 3})

    def test_quem_desliga_a_contribuicao_sai_da_soma(self):
        for p in self.pessoas[:3]:
            self.visita(p)
        self.client.force_authenticate(self.pessoas[0])
        r = self.client.patch("/api/me/", {"contribuir_motivos": False}, format="json")
        self.assertFalse(r.data["contribuir_motivos"])
        self.assertEqual(self.motivos(), {})
        self.client.force_authenticate(self.pessoas[0])
        self.client.patch("/api/me/", {"contribuir_motivos": True}, format="json")
        self.assertEqual(self.motivos(), {"cafe-colonial": 3})

    def test_minimo_configuravel(self):
        from django.test import override_settings

        with override_settings(MOTIVOS_MIN_PESSOAS=2):
            self.visita(self.pessoas[0])
            self.visita(self.pessoas[1])
            self.assertEqual(self.motivos(), {"cafe-colonial": 2})

    def test_lugar_sem_motivo_no_osm_passa_a_ser_sugerido(self):
        from lugares.models import Cidade

        Cidade.objects.create(nome="Lajeado", ponto=Point(-51.9617, -29.4669), id_externo="node/9")
        doceria = Lugar.objects.create(nome="Doceria da Vó", ponto=Point(-51.962, -29.467), fonte="osm",
                                       id_externo="node/77", cidade="Lajeado")  # o OSM não diz nada dela
        for p in self.pessoas[1:4]:
            self.visita(p, lugar=doceria, tags=("doces", "comida-caseira"))
        self.client.force_authenticate(self.pessoas[4])
        self.client.put("/api/me/preferencias/", {"tags": ["doces"]}, format="json")
        r = self.client.get("/api/sugestoes/", {"lat": -29.4669, "lng": -51.9617})
        primeira = r.data["resultados"][0]
        self.assertEqual(primeira["lugar"]["nome"], "Doceria da Vó")
        self.assertEqual(primeira["comunidade"], {"doces": 3})
