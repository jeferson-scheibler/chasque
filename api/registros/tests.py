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
