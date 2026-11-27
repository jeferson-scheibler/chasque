from django.contrib.gis.geos import Point
from django.core.cache import cache
from django.test import SimpleTestCase
from rest_framework.test import APITestCase

from contas.models import Usuario
from lugares.models import Lugar

from . import instagram
from .models import Salvo


class NormalizarTests(SimpleTestCase):
    def caso(self, entrada, url, tipo, perfil=""):
        link = instagram.normalizar(entrada)
        self.assertIsNotNone(link, entrada)
        self.assertEqual((link.url, link.tipo, link.perfil), (url, tipo, perfil))

    def test_reel_sem_rastreio(self):
        self.caso("https://www.instagram.com/reel/C9xYz12AbCd/?igsh=MWQ1ZGUxMzBkMA==",
                  "https://www.instagram.com/reel/C9xYz12AbCd/", "reel")

    def test_variacoes(self):
        self.caso("http://instagram.com/p/C9xYz12AbCd?utm_source=ig_web_copy_link",
                  "https://www.instagram.com/p/C9xYz12AbCd/", "post")
        self.caso("https://m.instagram.com/reels/C9xYz12AbCd/", "https://www.instagram.com/reel/C9xYz12AbCd/", "reel")
        self.caso("https://www.instagram.com/cafedapraca/reel/C9xYz12AbCd/",
                  "https://www.instagram.com/reel/C9xYz12AbCd/", "reel", "cafedapraca")
        self.caso("https://www.instagram.com/Cafe.Da_Praca?igsh=abc", "https://www.instagram.com/cafe.da_praca/",
                  "perfil", "cafe.da_praca")
        self.caso("https://www.instagram.com/stories/cafedapraca/3456789012/",
                  "https://www.instagram.com/cafedapraca/", "perfil", "cafedapraca")
        self.caso("https://www.instagram.com/share/reel/BAabc123XYZ/?igsh=x",
                  "https://www.instagram.com/share/reel/BAabc123XYZ/", "reel")

    def test_recusa_o_que_nao_e_post_nem_perfil(self):
        for url in [
            "https://www.instagram.com/explore/tags/lajeado/",
            "https://www.instagram.com/accounts/login/",
            "https://www.instagram.com/",
            "https://instagram.com.golpe.net/p/C9xYz12AbCd/",
            "https://www.tiktok.com/@x/video/1",
        ]:
            self.assertIsNone(instagram.normalizar(url), url)

    def test_encontrar_no_meio_do_texto(self):
        link = instagram.encontrar("", "Olha esse lugar! https://www.instagram.com/reel/C9xYz12AbCd/?igsh=x.")
        self.assertEqual(link.url, "https://www.instagram.com/reel/C9xYz12AbCd/")

    def test_limpar_texto(self):
        self.assertEqual(instagram.limpar_texto("https://www.instagram.com/reel/C9xYz12AbCd/?igsh=x"), "")
        self.assertEqual(instagram.limpar_texto("Café ótimo https://instagram.com/p/C9xYz12AbCd/"), "Café ótimo")


class SalvosTests(APITestCase):
    url = "/api/salvos/"
    reel = "https://www.instagram.com/reel/C9xYz12AbCd/?igsh=MWQ1ZGUxMzBkMA=="

    def setUp(self):
        cache.clear()
        self.ana = Usuario.objects.create_user(email="ana@exemplo.com", password="x" * 12, nome="Ana")
        self.bia = Usuario.objects.create_user(email="bia@exemplo.com", password="x" * 12, nome="Bia")
        self.client.force_authenticate(self.ana)
        self.lugar = Lugar.objects.create(nome="Café da Praça", ponto=Point(-51.96, -29.46), fonte="osm",
                                          id_externo="node/10")

    def compartilhar(self, **dados):
        return self.client.post(self.url, dados, format="json")

    def test_compartilhar_guarda_link_sem_rastreio(self):
        r = self.compartilhar(text=self.reel)
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["url"], "https://www.instagram.com/reel/C9xYz12AbCd/")
        self.assertEqual(r.data["tipo"], "reel")
        self.assertEqual(r.data["texto"], "")
        self.assertIsNone(r.data["lugar"])

    def test_guarda_a_legenda_colada(self):
        r = self.compartilhar(url=self.reel, text="Melhor cuca do Vale")
        self.assertEqual(r.data["texto"], "Melhor cuca do Vale")

    def test_compartilhar_de_novo_devolve_o_mesmo(self):
        primeiro = self.compartilhar(url=self.reel).data["id"]
        r = self.compartilhar(url="https://instagram.com/reel/C9xYz12AbCd/?igsh=outro", text="anotação")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["id"], primeiro)
        self.assertEqual(r.data["texto"], "anotação")
        self.assertEqual(Salvo.objects.count(), 1)

    def test_recusa_link_que_nao_e_do_instagram(self):
        r = self.compartilhar(url="https://www.tiktok.com/@x/video/1")
        self.assertEqual(r.status_code, 400)

    def test_vincular_ao_lugar_e_filtrar_pendentes(self):
        salvo = self.compartilhar(url=self.reel).data["id"]
        self.compartilhar(url="https://www.instagram.com/p/OUTROpost1/")
        self.assertEqual(len(self.client.get(self.url, {"pendentes": "1"}).data["results"]), 2)

        r = self.client.patch(f"{self.url}{salvo}/", {"lugar_id": self.lugar.id}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["lugar"]["nome"], "Café da Praça")
        self.assertEqual(len(self.client.get(self.url, {"pendentes": "1"}).data["results"]), 1)

    def test_nao_ve_nem_mexe_no_salvo_de_outra_pessoa(self):
        salvo = self.compartilhar(url=self.reel).data["id"]
        self.client.force_authenticate(self.bia)
        self.assertEqual(self.client.get(self.url).data["results"], [])
        self.assertEqual(self.client.get(f"{self.url}{salvo}/").status_code, 404)
        self.assertEqual(self.client.delete(f"{self.url}{salvo}/").status_code, 404)

    def test_url_nao_pode_ser_alterada(self):
        salvo = self.compartilhar(url=self.reel).data["id"]
        self.client.patch(f"{self.url}{salvo}/", {"url": "https://golpe.net/"}, format="json")
        self.assertEqual(Salvo.objects.get(pk=salvo).url, "https://www.instagram.com/reel/C9xYz12AbCd/")

    def test_excluir_e_exportar(self):
        salvo = self.compartilhar(url=self.reel, text="anotação").data["id"]
        exportado = self.client.get("/api/me/exportar/").data
        self.assertEqual(exportado["salvos"][0]["texto"], "anotação")
        self.assertEqual(self.client.delete(f"{self.url}{salvo}/").status_code, 204)
        self.assertFalse(Salvo.objects.exists())

    def test_varios_links_no_mesmo_lugar(self):
        primeiro = self.compartilhar(url=self.reel, lugar_id=self.lugar.id)
        self.assertEqual(primeiro.status_code, 201)
        self.assertFalse(primeiro.data["ja_salvo"])
        self.assertEqual(primeiro.data["lugar"]["id"], self.lugar.id)
        self.compartilhar(url="https://www.instagram.com/p/OUTROpost1/", lugar_id=self.lugar.id)
        self.compartilhar(url="https://www.instagram.com/p/DeOutroLugar/")
        do_lugar = self.client.get(self.url, {"lugar": self.lugar.id}).data["results"]
        self.assertEqual(len(do_lugar), 2)

        # compartilhar de novo um link já salvo avisa e pode trocar o lugar
        r = self.compartilhar(url="https://www.instagram.com/p/DeOutroLugar/", lugar_id=self.lugar.id)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data["ja_salvo"])
        self.assertEqual(len(self.client.get(self.url, {"lugar": self.lugar.id}).data["results"]), 3)

    def test_meus_lugares(self):
        from registros.models import Registro
        outro = Lugar.objects.create(nome="Cascata do Moinho", ponto=Point(-51.9, -29.4), fonte="osm",
                                     id_externo="node/11")
        alheio = Lugar.objects.create(nome="Bar da Bia", ponto=Point(-51.9, -29.4), fonte="osm", id_externo="node/12")
        self.compartilhar(url=self.reel, lugar_id=self.lugar.id)
        self.compartilhar(url="https://www.instagram.com/p/OUTROpost1/", lugar_id=self.lugar.id)
        Registro.objects.create(usuario=self.ana, lugar=outro, nota=5)
        Registro.objects.create(usuario=self.bia, lugar=alheio, nota=5)

        r = self.client.get("/api/meus-lugares/")
        self.assertEqual(r.status_code, 200)
        por_nome = {l["nome"]: l for l in r.data}
        self.assertEqual(set(por_nome), {"Café da Praça", "Cascata do Moinho"})
        self.assertEqual(por_nome["Café da Praça"]["links"], 2)
        self.assertFalse(por_nome["Café da Praça"]["visitado"])
        self.assertTrue(por_nome["Cascata do Moinho"]["visitado"])
        self.assertEqual([l["nome"] for l in self.client.get("/api/meus-lugares/", {"q": "cafe"}).data],
                         ["Café da Praça"])
