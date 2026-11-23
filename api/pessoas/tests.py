from django.contrib.gis.geos import Point
from django.core.cache import cache
from rest_framework.test import APITestCase

from contas.models import Usuario
from lugares.models import Lugar

from .models import Confianca


class PessoasTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.ana = Usuario.objects.create_user(email="ana@exemplo.com", password="x" * 12, nome="Ana Souza")
        self.bia = Usuario.objects.create_user(email="bia@exemplo.com", password="x" * 12, nome="Bia Lima")
        self.caio = Usuario.objects.create_user(email="caio@exemplo.com", password="x" * 12, nome="Caio")
        self.cafe = Lugar.objects.create(nome="Café da Praça", ponto=Point(-51.96, -29.46), fonte="osm", id_externo="n/1")

    def como(self, usuario):
        self.client.force_authenticate(usuario)
        return self.client

    def convite_de(self, usuario):
        return self.como(usuario).get("/api/pessoas/").data["convite"]

    def visita(self, usuario, privado, nota=5, ocasiao="casal", tags=("cafe-colonial",)):
        r = self.como(usuario).post("/api/registros/", {
            "lugar_id": self.cafe.id, "nota": nota, "ocasiao": ocasiao, "tags": list(tags), "privado": privado,
        }, format="json")
        assert r.status_code == 201, r.data
        return r.data["id"]

    def bia_segue_ana(self):
        codigo = self.convite_de(self.ana)
        self.como(self.bia).post(f"/api/convites/{codigo}/")
        pedido = self.como(self.ana).get("/api/pessoas/").data["pedidos"][0]
        self.como(self.ana).post(f"/api/confiancas/{pedido['id']}/aceitar/")
        return pedido["id"]

    def test_visita_nasce_privada(self):
        r = self.como(self.ana).post("/api/registros/", {
            "lugar_id": self.cafe.id, "nota": 5, "ocasiao": "casal", "tags": ["silencioso"],
        }, format="json")
        self.assertTrue(r.data["privado"])

    def test_convite_vira_pedido_e_so_aceito_libera(self):
        codigo = self.convite_de(self.ana)
        r = self.como(self.bia).get(f"/api/convites/{codigo}/")
        self.assertEqual((r.data["pessoa"]["nome"], r.data["estado"]), ("Ana Souza", None))
        r = self.como(self.bia).post(f"/api/convites/{codigo}/")
        self.assertEqual(r.data["estado"], "pendente")
        # pendente ainda não vê nada
        self.assertEqual(self.como(self.bia).get(f"/api/pessoas/{self.ana.id}/visitas/").status_code, 404)

        tela = self.como(self.ana).get("/api/pessoas/").data
        self.assertEqual([p["pessoa"]["nome"] for p in tela["pedidos"]], ["Bia Lima"])
        self.como(self.ana).post(f"/api/confiancas/{tela['pedidos'][0]['id']}/aceitar/")
        tela_bia = self.como(self.bia).get("/api/pessoas/").data
        self.assertEqual([p["pessoa"]["nome"] for p in tela_bia["seguindo"]], ["Ana Souza"])
        self.assertEqual(self.como(self.bia).get(f"/api/pessoas/{self.ana.id}/visitas/").status_code, 200)

    def test_so_visitas_liberadas_aparecem(self):
        self.visita(self.ana, privado=True)
        liberada = self.visita(self.ana, privado=False)
        self.bia_segue_ana()
        r = self.como(self.bia).get(f"/api/pessoas/{self.ana.id}/visitas/")
        self.assertEqual([v["id"] for v in r.data["results"]], [liberada])
        self.assertEqual(r.data["pessoa"]["nome"], "Ana Souza")
        self.assertEqual(self.como(self.bia).get("/api/pessoas/").data["seguindo"][0]["visitas"], 1)

    def test_filtro_por_ocasiao_e_so_as_boas(self):
        self.visita(self.ana, privado=False, ocasiao="familia")
        self.visita(self.ana, privado=False, ocasiao="casal", nota=2)
        self.bia_segue_ana()
        familia = self.como(self.bia).get(f"/api/pessoas/{self.ana.id}/visitas/", {"ocasiao": "familia"}).data
        self.assertEqual([v["ocasiao"] for v in familia["results"]], ["familia"])
        boas = self.como(self.bia).get(f"/api/pessoas/{self.ana.id}/visitas/", {"boas": "1"}).data
        self.assertEqual([v["nota"] for v in boas["results"]], [5])

    def test_confianca_nao_e_reciproca_nem_transitiva(self):
        self.visita(self.bia, privado=False)
        self.visita(self.caio, privado=False)
        self.bia_segue_ana()
        # a Ana não vê a Bia só porque a Bia segue a Ana
        self.assertEqual(self.como(self.ana).get(f"/api/pessoas/{self.bia.id}/visitas/").status_code, 404)
        # ninguém vê o Caio
        self.assertEqual(self.como(self.bia).get(f"/api/pessoas/{self.caio.id}/visitas/").status_code, 404)

    def test_desfazer_dos_dois_lados(self):
        conf = self.bia_segue_ana()
        self.assertEqual(self.como(self.caio).delete(f"/api/confiancas/{conf}/").status_code, 404)  # de terceiros não
        self.assertEqual(self.como(self.ana).delete(f"/api/confiancas/{conf}/").status_code, 204)  # remover seguidor
        self.assertEqual(self.como(self.bia).get(f"/api/pessoas/{self.ana.id}/visitas/").status_code, 404)
        conf = self.bia_segue_ana()
        self.assertEqual(self.como(self.bia).delete(f"/api/confiancas/{conf}/").status_code, 204)  # deixar de seguir
        self.assertFalse(Confianca.objects.exists())

    def test_so_quem_recebeu_aceita(self):
        codigo = self.convite_de(self.ana)
        self.como(self.bia).post(f"/api/convites/{codigo}/")
        conf = Confianca.objects.get()
        self.assertEqual(self.como(self.bia).post(f"/api/confiancas/{conf.id}/aceitar/").status_code, 404)
        self.assertEqual(self.como(self.caio).post(f"/api/confiancas/{conf.id}/aceitar/").status_code, 404)

    def test_trocar_codigo_invalida_o_link(self):
        antigo = self.convite_de(self.ana)
        novo = self.como(self.ana).post("/api/pessoas/convite/novo/").data["convite"]
        self.assertNotEqual(antigo, novo)
        self.assertEqual(self.como(self.bia).post(f"/api/convites/{antigo}/").status_code, 404)
        self.assertEqual(self.como(self.bia).post(f"/api/convites/{novo}/").status_code, 201)

    def test_nao_segue_a_si_mesmo_e_pedido_repetido_nao_duplica(self):
        codigo = self.convite_de(self.ana)
        self.assertEqual(self.como(self.ana).post(f"/api/convites/{codigo}/").status_code, 400)
        self.como(self.bia).post(f"/api/convites/{codigo}/")
        self.como(self.bia).post(f"/api/convites/{codigo}/")
        self.assertEqual(Confianca.objects.count(), 1)

    def test_nunca_mostra_email(self):
        self.bia_segue_ana()
        for usuario in (self.ana, self.bia):
            corpo = self.como(usuario).get("/api/pessoas/").content.decode()
            self.assertNotIn("@exemplo.com", corpo)
        codigo = self.convite_de(self.ana)
        self.assertNotIn("@", self.como(self.caio).get(f"/api/convites/{codigo}/").content.decode())

    def test_excluir_conta_desfaz_as_ligacoes_e_entra_na_exportacao(self):
        self.bia_segue_ana()
        exportado = self.como(self.bia).get("/api/me/exportar/").data
        self.assertEqual(exportado["pessoas_de_confianca"]["sigo"], ["Ana Souza"])
        self.como(self.ana).delete("/api/me/", {"senha": "x" * 12}, format="json")
        self.assertFalse(Confianca.objects.exists())
