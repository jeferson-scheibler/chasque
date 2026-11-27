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


class Intencao(models.Model):
    """Por que a pessoa salvou o link, lido do texto dela pela IA (ver docs/plano-intencao.md).

    É da pessoa: não entra nos motivos da comunidade nem aparece para pessoas de confiança. O lugar sugerido
    vem da nossa busca, a partir do nome que o texto indica; o modelo nunca escolhe um lugar da base.
    """

    class Estado(models.TextChoices):
        PENDENTE = "pendente", "Esperando leitura"
        PRONTA = "pronta", "Lida"
        FALHOU = "falhou", "Não deu para ler"
        CONFIRMADA = "confirmada", "Confirmada pela pessoa"

    class Confianca(models.TextChoices):
        ALTA = "alta", "Alta"
        MEDIA = "media", "Média"
        BAIXA = "baixa", "Baixa"

    salvo = models.OneToOneField(Salvo, on_delete=models.CASCADE, related_name="intencao")
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PENDENTE, db_index=True)
    frase = models.CharField(max_length=120, blank=True, help_text="O motivo, na voz da pessoa.")
    tags = models.ManyToManyField("lugares.Tag", blank=True, related_name="intencoes")
    confianca = models.CharField(max_length=5, choices=Confianca.choices, blank=True)
    lugar_nome = models.CharField(max_length=200, blank=True, help_text="Nome do lugar como o texto indica.")
    lugar_cidade = models.CharField(max_length=120, blank=True)
    lugar_sugerido = models.ForeignKey(
        "lugares.Lugar", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    hash_entrada = models.CharField(max_length=64, blank=True, help_text="Para não ler de novo o mesmo texto.")
    modelo = models.CharField(max_length=60, blank=True)
    versao_prompt = models.CharField(max_length=20, blank=True)
    tentativas = models.PositiveSmallIntegerField(default=0)
    lida_em = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "intenção"
        verbose_name_plural = "intenções"

    def __str__(self):
        return f"{self.salvo}: {self.frase or self.get_estado_display()}"
