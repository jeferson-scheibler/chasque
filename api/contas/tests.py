from django.conf import settings
from django.contrib.gis.geos import Point
from django.core.cache import cache
from rest_framework.test import APITestCase

from lugares.models import Lugar, Tag
from registros.models import Registro

from .models import Usuario

COOKIE = settings.REFRESH_COOKIE["name"]
SENHA = "uma-senha-bem-longa-42"


class Base(APITestCase):
    def setUp(self):
        cache.clear()  # zera os limites de tentativas entre testes

    def criar_usuario(self, email="ana@exemplo.com"):
        return Usuario.objects.create_user(email=email, password=SENHA, nome="Ana")

    def entrar(self, mobile=False, email="ana@exemplo.com", senha=SENHA):
        headers = {"HTTP_X_CHASQUE_CLIENTE": "mobile"} if mobile else {}
        return self.client.post("/api/auth/entrar/", {"email": email, "senha": senha}, format="json", **headers)


class SaudeTests(APITestCase):
    def test_healthz(self):
        r = self.client.get("/api/healthz")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"status": "ok"})


class CadastroTests(Base):
    url = "/api/auth/cadastro/"

    def dados(self, **extra):
        return {"email": "Bia@Exemplo.com ", "nome": "Bia", "senha": SENHA, "aceita_termos": True, **extra}

    def test_cadastro_cria_conta_e_registra_consentimento(self):
        r = self.client.post(self.url, self.dados(), format="json")
        self.assertEqual(r.status_code, 201, r.content)
        usuario = Usuario.objects.get()
        self.assertEqual(usuario.email, "bia@exemplo.com")
        self.assertIsNotNone(usuario.termos_aceitos_em)
        self.assertEqual(usuario.versao_termos, settings.VERSAO_TERMOS)
        self.assertTrue(usuario.password.startswith("argon2"))
        self.assertIn("access", r.data)

    def test_cadastro_exige_aceite_dos_termos(self):
        r = self.client.post(self.url, self.dados(aceita_termos=False), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("aceita_termos", r.data)
        self.assertFalse(Usuario.objects.exists())

    def test_cadastro_recusa_senha_fraca(self):
        r = self.client.post(self.url, self.dados(senha="12345678"), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("senha", r.data)

    def test_cadastro_recusa_email_repetido_sem_diferenciar_maiusculas(self):
        self.criar_usuario("bia@exemplo.com")
        r = self.client.post(self.url, self.dados(), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("email", r.data)


class EntrarTests(Base):
    def setUp(self):
        super().setUp()
        self.criar_usuario()

    def test_web_recebe_refresh_so_em_cookie_httponly(self):
        r = self.entrar()
        self.assertEqual(r.status_code, 200)
        self.assertIn("access", r.data)
        self.assertNotIn("refresh", r.data)
        cookie = r.cookies[COOKIE]
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["path"], "/api/auth/")
        self.assertEqual(cookie["samesite"], "Lax")

    def test_mobile_recebe_refresh_no_corpo(self):
        r = self.entrar(mobile=True)
        self.assertEqual(r.status_code, 200)
        self.assertIn("refresh", r.data)
        self.assertNotIn(COOKIE, r.cookies)

    def test_senha_errada_e_email_inexistente_dao_a_mesma_resposta(self):
        r1 = self.entrar(senha="errada-errada-errada")
        r2 = self.entrar(email="ninguem@exemplo.com")
        self.assertEqual(r1.status_code, 401)
        self.assertEqual(r2.status_code, 401)
        self.assertEqual(r1.data, r2.data)

    def test_limite_de_tentativas(self):
        codigos = [self.entrar(senha="errada-errada-errada").status_code for _ in range(11)]
        self.assertEqual(codigos[-1], 429)


class RenovarSairTests(Base):
    def setUp(self):
        super().setUp()
        self.criar_usuario()

    def test_renovar_pelo_cookie_rotaciona_e_nao_expoe_o_token(self):
        self.entrar()
        antigo = self.client.cookies[COOKIE].value
        r = self.client.post("/api/auth/renovar/", {}, format="json", HTTP_X_CHASQUE_CLIENTE="mobile")
        self.assertEqual(r.status_code, 200)
        self.assertIn("access", r.data)
        # Mesmo pedindo como mobile, token que veio de cookie nao vai para o corpo.
        self.assertNotIn("refresh", r.data)
        self.assertNotEqual(r.cookies[COOKIE].value, antigo)

        # O refresh antigo foi para a lista negra.
        r = self.client.post("/api/auth/renovar/", {"refresh": antigo}, format="json")
        self.assertEqual(r.status_code, 401)

    def test_renovar_mobile_pelo_corpo(self):
        refresh = self.entrar(mobile=True).data["refresh"]
        r = self.client.post("/api/auth/renovar/", {"refresh": refresh}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertIn("refresh", r.data)

    def test_sair_invalida_o_refresh(self):
        refresh = self.entrar(mobile=True).data["refresh"]
        r = self.client.post("/api/auth/sair/", {"refresh": refresh}, format="json")
        self.assertEqual(r.status_code, 204)
        r = self.client.post("/api/auth/renovar/", {"refresh": refresh}, format="json")
        self.assertEqual(r.status_code, 401)

    def test_renovar_sem_token(self):
        r = self.client.post("/api/auth/renovar/", {}, format="json")
        self.assertEqual(r.status_code, 401)


class MeTests(Base):
    def setUp(self):
        super().setUp()
        self.usuario = self.criar_usuario()
        self.access = self.entrar(mobile=True).data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")

    def criar_registro(self, usuario=None):
        lugar = Lugar.objects.create(nome="Cafe da Praca", ponto=Point(-51.96, -29.46), fonte="usuario")
        registro = Registro.objects.create(usuario=usuario or self.usuario, lugar=lugar, ocasiao="casal", nota=5)
        registro.tags.add(Tag.objects.get(slug="cafe-colonial"))
        return registro

    def test_me_exige_login(self):
        self.client.credentials()
        self.assertEqual(self.client.get("/api/me/").status_code, 401)

    def test_ver_e_editar_perfil(self):
        r = self.client.patch("/api/me/", {"cidade_base": "Lajeado", "email": "outro@x.com"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.cidade_base, "Lajeado")
        self.assertEqual(self.usuario.email, "ana@exemplo.com")  # e-mail e somente leitura

    def test_exportar_traz_os_registros(self):
        self.criar_registro()
        r = self.client.get("/api/me/exportar/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("attachment", r["Content-Disposition"])
        self.assertEqual(r.data["registros"][0]["lugar"]["nome"], "Cafe da Praca")
        self.assertEqual(r.data["registros"][0]["tags"], ["cafe-colonial"])

    def test_excluir_conta_exige_senha(self):
        r = self.client.delete("/api/me/", {"senha": "errada"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertTrue(Usuario.objects.filter(pk=self.usuario.pk).exists())

    def test_excluir_conta_apaga_registros_e_invalida_sessoes(self):
        self.criar_registro()
        outro = self.criar_usuario("outro@exemplo.com")
        self.criar_registro(outro)

        refresh = self.entrar(mobile=True).data["refresh"]
        r = self.client.delete("/api/me/", {"senha": SENHA}, format="json")
        self.assertEqual(r.status_code, 204)

        self.assertFalse(Usuario.objects.filter(email="ana@exemplo.com").exists())
        self.assertEqual(Registro.objects.count(), 1)  # so o do outro usuario
        self.assertEqual(self.client.get("/api/me/").status_code, 401)
        r = self.client.post("/api/auth/renovar/", {"refresh": refresh}, format="json")
        self.assertEqual(r.status_code, 401)
