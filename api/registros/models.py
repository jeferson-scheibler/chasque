from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class Ocasiao(models.TextChoices):
    SOZINHO = "sozinho", "Sozinho"
    CASAL = "casal", "Casal"
    FAMILIA = "familia", "Família"
    AMIGOS = "amigos", "Amigos"
    TRABALHO = "trabalho", "Trabalho"
    GRUPO = "grupo", "Evento ou grupo"


class Registro(models.Model):
    """Uma visita: onde, quando, com quem e por que gostou (ou nao)."""

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="registros")
    lugar = models.ForeignKey("lugares.Lugar", on_delete=models.PROTECT, related_name="registros")
    visitado_em = models.DateField(default=timezone.localdate)
    ocasiao = models.CharField(max_length=20, choices=Ocasiao.choices)
    nota = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    tags = models.ManyToManyField("lugares.Tag", blank=True, related_name="registros")
    motivo = models.TextField(max_length=500, blank=True)
    # Privado por padrao: so o dono ve, ate existir a camada de pessoas de confianca.
    privado = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["usuario", "-visitado_em"], name="registro_usuario_data")]

    def __str__(self):
        return f"{self.usuario} em {self.lugar} ({self.visitado_em})"


class PreferenciaDeclarada(models.Model):
    """Gosto escolhido no onboarding. Da sugestao antes do primeiro registro."""

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="preferencias")
    tag = models.ForeignKey("lugares.Tag", on_delete=models.CASCADE)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["usuario", "tag"], name="preferencia_unica")]


class PesoGosto(models.Model):
    """Perfil de gosto calculado. ocasiao vazia = vale para qualquer ocasiao."""

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pesos")
    tag = models.ForeignKey("lugares.Tag", on_delete=models.CASCADE)
    ocasiao = models.CharField(max_length=20, choices=Ocasiao.choices, blank=True)
    peso = models.FloatField(default=0)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["usuario", "tag", "ocasiao"], name="peso_unico"),
        ]
