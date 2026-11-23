from django.conf import settings
from django.db import models


class Salvo(models.Model):
    """Lugar que a pessoa quer conhecer, vindo de um compartilhamento (por enquanto, do Instagram)."""

    class Origem(models.TextChoices):
        INSTAGRAM = "instagram", "Instagram"

    class Tipo(models.TextChoices):
        POST = "post", "Post"
        REEL = "reel", "Reel"
        PERFIL = "perfil", "Perfil"

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="salvos")
    # Vazio até a pessoa dizer qual é o lugar.
    lugar = models.ForeignKey(
        "lugares.Lugar", null=True, blank=True, on_delete=models.SET_NULL, related_name="salvos"
    )
    origem = models.CharField(max_length=20, choices=Origem.choices, default=Origem.INSTAGRAM)
    url = models.URLField(max_length=300, help_text="Link sem parâmetros de rastreio.")
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    perfil = models.CharField(max_length=30, blank=True, help_text="@ do Instagram, quando vem no link.")
    texto = models.TextField(max_length=2000, blank=True, help_text="Legenda colada ou anotação da pessoa.")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-criado_em"]
        constraints = [models.UniqueConstraint(fields=["usuario", "url"], name="salvo_unico_por_usuario")]

    def __str__(self):
        return f"{self.usuario} salvou {self.url}"
