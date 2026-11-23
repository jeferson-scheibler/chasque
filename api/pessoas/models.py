import secrets

from django.conf import settings
from django.db import models


def novo_codigo():
    return secrets.token_urlsafe(9)  # 12 caracteres, impossível de adivinhar


class Convite(models.Model):
    """Link pessoal para alguém pedir para seguir. Trocar o código invalida o link antigo."""

    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="convite")
    codigo = models.CharField(max_length=24, unique=True, default=novo_codigo)
    criado_em = models.DateTimeField(auto_now=True)

    @classmethod
    def de(cls, usuario):
        convite, _ = cls.objects.get_or_create(usuario=usuario)
        return convite


class Confianca(models.Model):
    """`seguidor` vê as visitas que `seguido` liberou para pessoas de confiança, depois que `seguido` aceita."""

    class Estado(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        ACEITO = "aceito", "Aceito"

    seguidor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="confianca_dada")
    seguido = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="confianca_recebida")
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDENTE)
    criado_em = models.DateTimeField(auto_now_add=True)
    aceito_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "confiança"
        verbose_name_plural = "confianças"
        constraints = [
            models.UniqueConstraint(fields=["seguidor", "seguido"], name="confianca_unica"),
            models.CheckConstraint(condition=~models.Q(seguidor=models.F("seguido")), name="confianca_nao_em_si"),
        ]

    def __str__(self):
        return f"{self.seguidor} -> {self.seguido} ({self.estado})"
