from django.conf import settings
from django.db import models


class Agenda(models.Model):
    """Endereço secreto (iCal) da agenda da pessoa. Só os horários ocupados são lidos; títulos, lugares e
    convidados dos eventos nunca são guardados."""

    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="agenda")
    url = models.TextField(help_text="Endereço secreto. Nunca volta para o app inteiro.")
    servico = models.CharField(max_length=120, help_text="Só o domínio, para mostrar de onde vem a agenda.")
    lida_em = models.DateTimeField(null=True, blank=True)
    erro = models.CharField(max_length=200, blank=True)
    dias_livres = models.JSONField(default=list, blank=True, help_text="Sábados e domingos livres, em ISO.")
    criada_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Agenda de {self.usuario} ({self.servico})"


class Roteiro(models.Model):
    """Roteiro de um dia livre de fim de semana, montado com os lugares salvos da pessoa."""

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="roteiros")
    dia = models.DateField()
    cidade = models.CharField(max_length=120, blank=True)
    viagem = models.BooleanField(default=False, help_text="Fora da cidade base da pessoa.")
    criado_em = models.DateTimeField(auto_now_add=True)
    notificado_em = models.DateTimeField(null=True, blank=True)
    visto_em = models.DateTimeField(null=True, blank=True)
    dispensado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["dia"]
        constraints = [models.UniqueConstraint(fields=["usuario", "dia"], name="roteiro_unico_por_dia")]

    def __str__(self):
        return f"Roteiro de {self.usuario} em {self.dia}"


class Parada(models.Model):
    class Momento(models.TextChoices):
        MANHA = "manha", "Manhã"
        ALMOCO = "almoco", "Almoço"
        TARDE = "tarde", "Tarde"
        NOITE = "noite", "Noite"

    roteiro = models.ForeignKey(Roteiro, on_delete=models.CASCADE, related_name="paradas")
    lugar = models.ForeignKey("lugares.Lugar", on_delete=models.CASCADE, related_name="paradas")
    ordem = models.PositiveSmallIntegerField()
    momento = models.CharField(max_length=10, choices=Momento.choices)
    salvo = models.BooleanField(default=False, help_text="Veio da lista da pessoa (e não de uma sugestão).")

    class Meta:
        ordering = ["ordem"]


class InscricaoPush(models.Model):
    """Aparelho que aceitou receber avisos (Web Push)."""

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="inscricoes_push")
    endpoint = models.URLField(max_length=1000, unique=True)
    p256dh = models.CharField(max_length=200)
    auth = models.CharField(max_length=100)
    criada_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Push de {self.usuario}"
