import json
import tempfile

from django.contrib.gis.geos import Point
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APITestCase

from contas.models import Usuario

from . import osm
from .models import Cidade, Lugar


def feature(tipo, id_, tags, lng, lat, poligono=False):
    if poligono:
        d = 0.0005
        geometria = {"type": "Polygon", "coordinates": [[
            [lng - d, lat - d], [lng + d, lat - d], [lng + d, lat + d], [lng - d, lat + d], [lng - d, lat - d]
        ]]}
    else:
        geometria = {"type": "Point", "coordinates": [lng, lat]}
    return {"type": "Feature", "geometry": geometria, "properties": {"@type": tipo, "@id": id_, **tags}}


AMOSTRA = [
    feature("node", 10, {"amenity": "cafe", "name": "Café da Praça", "outdoor_seating": "yes",
                         "addr:street": "Rua Júlio de Castilhos", "addr:housenumber": "100"}, -51.9620, -29.4672),
    feature("way", 20, {"tourism": "viewpoint", "name": "Mirante do Morro"}, -51.9400, -29.4800, poligono=True),
    feature("node", 30, {"amenity": "restaurant", "name": "Churrascaria Gaúcha", "cuisine": "barbecue;regional",
                         "addr:city": "Estrela"}, -51.9551, -29.5021),
    feature("node", 40, {"amenity": "bench"}, -51.96, -29.46),  # categoria que não interessa
    feature("node", 50, {"amenity": "restaurant"}, -51.96, -29.46),  # sem nome
]


class ClassificacaoTests(TestCase):
    def test_classificar(self):
        self.assertEqual(osm.classificar({"amenity": "cafe"}), "amenity=cafe")
        self.assertEqual(osm.classificar({"craft": "winery", "shop": "wine"}), "craft=winery")
        self.assertIsNone(osm.classificar({"amenity": "parking"}))
        self.assertIsNone(osm.classificar({"leisure": "garden", "access": "private"}))

    def test_tags_iniciais(self):
        self.assertEqual(osm.tags_iniciais({"tourism": "viewpoint"}, "tourism=viewpoint"), {"vista-bonita"})
        tags = osm.tags_iniciais({"cuisine": "barbecue;regional", "wheelchair": "yes", "dog": "yes"}, "amenity=restaurant")
        self.assertEqual(tags, {"churrasco", "comida-caseira", "acessivel", "aceita-pet"})
        self.assertEqual(osm.tags_iniciais({}, "amenity=restaurant"), set())

    def test_endereco(self):
        self.assertEqual(osm.endereco({"addr:street": "Rua A", "addr:housenumber": "5"}), "Rua A, 5")
        self.assertEqual(osm.endereco({"addr:housenumber": "5"}), "")


class ImportacaoTests(TestCase):
    def setUp(self):
        Cidade.objects.create(nome="Lajeado", ponto=Point(-51.9617, -29.4669), id_externo="node/1")
        Cidade.objects.create(nome="Estrela", ponto=Point(-51.9550, -29.5020), id_externo="node/2")

    def importar(self, features=AMOSTRA):
        with tempfile.NamedTemporaryFile("w", suffix=".geojsonseq", delete=False, encoding="utf-8") as arquivo:
            for f in features:
                arquivo.write("\x1e" + json.dumps(f) + "\n")
        call_command("importar_osm", geojson=arquivo.name, stdout=open("/dev/null", "w"))

    def test_importa_lugares(self):
        self.importar()
        self.assertEqual(Lugar.objects.count(), 3)

        cafe = Lugar.objects.get(id_externo="node/10")
        self.assertEqual(cafe.fonte, "osm")
        self.assertEqual(cafe.categoria, "amenity=cafe")
        self.assertEqual(cafe.endereco, "Rua Júlio de Castilhos, 100")
        self.assertEqual(cafe.cidade, "Lajeado")  # cidade mais próxima
        self.assertEqual(set(cafe.tags.values_list("slug", flat=True)), {"ao-ar-livre"})

        mirante = Lugar.objects.get(id_externo="way/20")
        self.assertAlmostEqual(mirante.ponto.x, -51.94, places=3)  # ponto dentro do polígono

        churrascaria = Lugar.objects.get(id_externo="node/30")
        self.assertEqual(churrascaria.cidade, "Estrela")  # addr:city tem prioridade

    def test_rodar_de_novo_atualiza_sem_duplicar(self):
        self.importar()
        alterado = [f for f in AMOSTRA if f["properties"]["@id"] != 10]
        alterado.append(feature("node", 10, {"amenity": "cafe", "name": "Café da Praça Nova"}, -51.9620, -29.4672))
        self.importar(alterado)
        self.assertEqual(Lugar.objects.count(), 3)
        self.assertEqual(Lugar.objects.get(id_externo="node/10").nome, "Café da Praça Nova")


class MunicipiosTests(TestCase):
    OPL = (
        "r10 v1 dV c1 t2020-01-01T00:00:00Z i1 utest "
        "Tadmin_level=8,boundary=administrative,IBGE:GEOCODIGO=4311403,name=Lajeado Mw1@outer,n500@admin_centre\n"
        "r11 v1 dV c1 t2020-01-01T00:00:00Z i1 utest "
        "Tadmin_level=8,IBGE:GEOCODIGO=4316402,name=S%e3%o%20%Valentim%20%do%20%Sul Mw2@outer,n501@admin_centre\n"
        "r12 v1 dV c1 t2020-01-01T00:00:00Z i1 utest "
        "Tadmin_level=8,IBGE:GEOCODIGO=4202305,name=Bom%20%Jesus Mw3@outer,n502@admin_centre\n"  # SC: fica de fora
        "r13 v1 dV c1 t2020-01-01T00:00:00Z i1 utest Tadmin_level=8,IBGE:GEOCODIGO=4300000,name=Sem%20%sede Mw4@outer\n"
    )

    def arquivo(self, texto):
        with tempfile.NamedTemporaryFile("w", suffix=".opl", delete=False, encoding="utf-8") as arq:
            arq.write(texto)
        return arq.name

    def test_le_so_municipios_da_uf_com_sede(self):
        municipios = osm.ler_municipios_opl(self.arquivo(self.OPL), "43")
        self.assertEqual(municipios, {
            "500": {"nome": "Lajeado", "ibge": "4311403"},
            "501": {"nome": "São Valentim do Sul", "ibge": "4316402"},
        })

    def test_le_posicao_dos_nos(self):
        nos = osm.ler_nos_opl(self.arquivo("n500 v3 dV c1 t2020-01-01T00:00:00Z i1 utest T x-51.9617 y-29.4669\n"))
        self.assertEqual(nos, {"500": (-51.9617, -29.4669)})

    def test_importar_municipios_atualiza_sem_duplicar(self):
        lista = [{"nome": "Lajeado", "ibge": "4311403", "no": "500", "lng": -51.96, "lat": -29.46}]
        self.assertEqual(osm.importar_municipios(lista), {"cidades": 1, "novas": 1})
        lista[0]["nome"] = "Lajeado (sede)"
        self.assertEqual(osm.importar_municipios(lista), {"cidades": 1, "novas": 0})
        cidade = Cidade.objects.get()
        self.assertEqual((cidade.nome, cidade.codigo_ibge, cidade.id_externo), ("Lajeado (sede)", "4311403", "node/500"))


class Autenticado(APITestCase):
    def setUp(self):
        cache.clear()
        self.usuario = Usuario.objects.create_user(email="ana@exemplo.com", password="x" * 12, nome="Ana")
        self.client.force_authenticate(self.usuario)
        self.lajeado = Cidade.objects.create(nome="Lajeado", ponto=Point(-51.9617, -29.4669), id_externo="node/1")
        self.cafe = Lugar.objects.create(nome="Café da Praça", ponto=Point(-51.9620, -29.4672), fonte="osm",
                                         id_externo="node/10", cidade="Lajeado", categoria="amenity=cafe")
        self.longe = Lugar.objects.create(nome="Café Colonial da Serra", ponto=Point(-52.20, -29.00), fonte="osm",
                                          id_externo="node/11")
        Lugar.objects.create(nome="Padaria Central", ponto=Point(-51.9625, -29.4675), fonte="osm", id_externo="node/12")


class BuscaTests(Autenticado):
    def buscar(self, **params):
        return self.client.get("/api/lugares/", params)

    def test_busca_ignora_acento_e_maiusculas(self):
        r = self.buscar(q="CAFE DA PRACA")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data[0]["nome"], "Café da Praça")
        self.assertEqual(r.data[0]["categoria_nome"], "Café")
        self.assertEqual(r.data[0]["cidade"], "Lajeado")

    def test_busca_tolera_erro_de_digitacao(self):
        nomes = [l["nome"] for l in self.buscar(q="cafe da prasa").data]
        self.assertIn("Café da Praça", nomes)

    def test_busca_por_proximidade(self):
        r = self.buscar(q="cafe", lat=-29.4672, lng=-51.9620)
        self.assertEqual([l["nome"] for l in r.data][:2], ["Café da Praça", "Café Colonial da Serra"])
        self.assertEqual(r.data[0]["distancia_m"], 0)

    def test_sem_parametros(self):
        self.assertEqual(self.buscar().status_code, 400)

    def test_exige_login(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.buscar(q="cafe").status_code, 401)

    def test_um_lugar_pelo_id(self):
        r = self.client.get(f"/api/lugares/{self.cafe.id}/")
        self.assertEqual((r.status_code, r.data["nome"]), (200, "Café da Praça"))
        self.assertEqual(self.client.get("/api/lugares/999999/").status_code, 404)

    def test_lista_cidades(self):
        r = self.client.get("/api/cidades/")
        self.assertEqual(r.data, [{"id": self.lajeado.id, "nome": "Lajeado", "lat": -29.4669, "lng": -51.9617}])


class CriarLugarTests(Autenticado):
    url = "/api/lugares/"

    def test_cria_pela_cidade_com_posicao_aproximada(self):
        r = self.client.post(self.url, {"nome": "Bistrô Novo", "cidade_id": self.lajeado.id}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        lugar = Lugar.objects.get(pk=r.data["id"])
        self.assertTrue(lugar.aproximado)
        self.assertEqual(lugar.fonte, "usuario")
        self.assertEqual(lugar.criado_por, self.usuario)
        self.assertEqual(lugar.cidade, "Lajeado")

    def test_cria_pela_localizacao_e_acha_a_cidade(self):
        r = self.client.post(self.url, {"nome": "Bistrô Novo", "lat": -29.47, "lng": -51.96}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertFalse(r.data["aproximado"])
        self.assertEqual(r.data["cidade"], "Lajeado")

    def test_exige_cidade_ou_posicao(self):
        r = self.client.post(self.url, {"nome": "Bistrô Novo"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_mesmo_nome_perto_devolve_o_existente(self):
        r = self.client.post(self.url, {"nome": "cafe da praca", "lat": -29.4673, "lng": -51.9621}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["id"], self.cafe.id)


class HorariosTests(TestCase):
    SEGUNDA, SABADO, DOMINGO = __import__("datetime").date(2026, 11, 30), __import__("datetime").date(2026, 11, 28), __import__("datetime").date(2026, 11, 29)

    def estado(self, horario, data, hora=None):
        from . import horarios

        return horarios.estado(horario, data, None if hora is None else int(hora[:2]) * 60 + int(hora[3:]))

    def test_dia_listado_abre_e_dia_de_fora_fecha(self):
        h = "Mo-Fr 08:00-18:00; Sa 09:00-13:00"
        self.assertEqual(self.estado(h, self.SEGUNDA), "aberto")
        self.assertEqual(self.estado(h, self.SABADO), "aberto")
        self.assertEqual(self.estado(h, self.DOMINGO), "fechado")

    def test_off_e_regra_mais_nova_vence(self):
        self.assertEqual(self.estado("Mo-Su 10:00-22:00; Mo off", self.SEGUNDA), "fechado")
        self.assertEqual(self.estado("Mo-Su 10:00-22:00; Mo off", self.DOMINGO), "aberto")

    def test_hora_dentro_e_fora_do_intervalo(self):
        h = "Mo-Su 11:00-14:00,18:00-23:00"
        self.assertEqual(self.estado(h, self.SEGUNDA, "12:00"), "aberto")
        self.assertEqual(self.estado(h, self.SEGUNDA, "15:30"), "fechado")
        self.assertEqual(self.estado(h, self.SEGUNDA, "19:00"), "aberto")

    def test_passa_da_meia_noite_vale_para_o_dia_seguinte_cedo(self):
        h = "Su 18:00-02:00"  # abre domingo e vai até segunda de madrugada
        self.assertEqual(self.estado(h, self.DOMINGO, "23:00"), "aberto")
        self.assertEqual(self.estado(h, self.SEGUNDA, "01:00"), "aberto")
        self.assertEqual(self.estado(h, self.SEGUNDA, "03:00"), "fechado")

    def test_virgula_antes_de_dia_soma_regra(self):
        h = "Mo-Fr 11:30-14:30, Sa 12:00-00:00, Su 12:00-15:30"
        self.assertEqual(self.estado(h, self.SEGUNDA, "12:00"), "aberto")
        self.assertEqual(self.estado(h, self.SABADO, "22:00"), "aberto")
        self.assertEqual(self.estado(h, self.DOMINGO, "18:00"), "fechado")
        # a vírgula soma no mesmo dia: almoço de segunda a sexta e jantar na sexta
        self.assertEqual(self.estado("Mo-Fr 11:00-14:00, Fr 19:00-23:00", self.SEGUNDA, "20:00"), "fechado")
        # vírgula entre dias do mesmo seletor não é regra nova
        self.assertEqual(self.estado("Sa, Su 10:00-22:00; Tu-Fr 11:30-22:00", self.DOMINGO), "aberto")
        self.assertEqual(self.estado("Mo-Tu,Th 10:00-23:00; Fr-Sa 10:00-00:00", self.SEGUNDA), "aberto")
        self.assertEqual(self.estado("Mo-Fr 07:00-19:00; Su, PH off", self.DOMINGO), "fechado")

    def test_vinte_e_quatro_sete(self):
        self.assertEqual(self.estado("24/7", self.SEGUNDA, "04:00"), "aberto")

    def test_o_que_nao_entende_vira_nao_sei(self):
        for h in ("", "Mo-Fr 08:00+", "Apr-Oct Mo-Fr 09:00-17:00", "sunrise-sunset", "Mo-Fr 08:00-12:00 || \"ligue\"", "PH off"):
            self.assertIsNone(self.estado(h, self.SEGUNDA), h)

    def test_feriado_e_ignorado_sem_quebrar_a_semana(self):
        self.assertEqual(self.estado("Mo-Fr 08:00-18:00; PH off", self.SEGUNDA), "aberto")

    def test_texto_do_dia(self):
        from . import horarios

        self.assertEqual(horarios.texto_do_dia("Mo-Su 11:00-14:00,18:00-23:00", self.SEGUNDA), "11:00 às 14:00 e 18:00 às 23:00")
        self.assertEqual(horarios.texto_do_dia("24/7", self.SEGUNDA), "o dia todo")
        self.assertEqual(horarios.texto_do_dia("Mo-Fr 08:00-18:00", self.DOMINGO), "")

    def test_importacao_guarda_horario_e_telefone(self):
        osm.importar([feature("node", 91, {"amenity": "bar", "name": "Bar da Esquina", "opening_hours": "Tu-Su 18:00-23:00",
                                           "contact:phone": "+55 51 99999-0000; +55 51 3333-0000"}, -51.96, -29.46)])
        bar = Lugar.objects.get(id_externo="node/91")
        self.assertEqual(bar.horario, "Tu-Su 18:00-23:00")
        self.assertEqual(bar.telefone, "+55 51 99999-0000")
