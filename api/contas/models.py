from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    @staticmethod
    def normalizar_email(email):
        return (email or "").strip().lower()

    def _criar(self, email, password, **extra):
        if not email:
            raise ValueError("O e-mail é obrigatório.")
        usuario = self.model(email=self.normalizar_email(email), **extra)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._criar(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra["is_staff"] = True
        extra["is_superuser"] = True
        return self._criar(email, password, **extra)

    def get_by_natural_key(self, email):
        return self.get(email=self.normalizar_email(email))


class Usuario(AbstractUser):
    """Login por e-mail. Sem username, sem first/last name."""

    username = None
    first_name = None
    last_name = None

    email = models.EmailField("e-mail", unique=True)
    nome = models.CharField(max_length=120)
    cidade_base = models.CharField("cidade base", max_length=120, blank=True)

    # Motivos de visitas bem avaliadas entram, somados aos de outras pessoas e sem nome, na descrição do lugar.
    contribuir_motivos = models.BooleanField(default=True)

    # LGPD: registro do consentimento.
    termos_aceitos_em = models.DateTimeField(null=True, blank=True)
    versao_termos = models.CharField(max_length=20, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nome"]

    objects = UsuarioManager()

    class Meta:
        verbose_name = "usuário"
        verbose_name_plural = "usuários"

    def __str__(self):
        return self.email
