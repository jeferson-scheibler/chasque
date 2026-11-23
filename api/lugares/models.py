from django.contrib.gis.db import models


class Tag(models.Model):
    """Motivo pelo qual alguem gosta de um lugar. Base do perfil de gosto."""

    class Grupo(models.TextChoices):
        AMBIENTE = "ambiente", "Ambiente"
        PRECO = "preco", "Preço"
        COMIDA = "comida", "Comida e bebida"
        SERVICO = "servico", "Serviço"
        EXPERIENCIA = "experiencia", "Experiência"

    slug = models.SlugField(max_length=40, unique=True)
    nome = models.CharField(max_length=60)
    grupo = models.CharField(max_length=20, choices=Grupo.choices)

    class Meta:
        ordering = ["grupo", "nome"]

    def __str__(self):
        return self.nome


class Cidade(models.Model):
    """Sede de município (admin_centre da relação do município no OSM). Serve para lugar criado sem posição exata."""

    nome = models.CharField(max_length=120)
    ponto = models.PointField(geography=True, srid=4326)
    id_externo = models.CharField(max_length=80, unique=True)
    codigo_ibge = models.CharField("código IBGE", max_length=7, blank=True, db_index=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Lugar(models.Model):
    class Fonte(models.TextChoices):
        OSM = "osm", "OpenStreetMap"
        OVERTURE = "overture", "Overture Maps"
        USUARIO = "usuario", "Usuário"
        NEGOCIO = "negocio", "Negócio"

    nome = models.CharField(max_length=200)
    endereco = models.CharField(max_length=300, blank=True)
    # geography=True: distancias em metros, sem conversao de projecao.
    ponto = models.PointField(geography=True, srid=4326)
    categoria = models.CharField(max_length=60, blank=True, db_index=True)
    fonte = models.CharField(max_length=20, choices=Fonte.choices)
    id_externo = models.CharField(
        max_length=80,
        blank=True,
        help_text="Id na fonte de origem (ex.: node/123 no OSM). Do Google, so o place ID.",
    )
    cidade = models.CharField(max_length=120, blank=True)
    # True quando a posição é só o centro da cidade (lugar criado sem localização exata).
    aproximado = models.BooleanField(default=False)
    verificado = models.BooleanField(default=False)
    tags = models.ManyToManyField(Tag, blank=True, related_name="lugares")
    criado_por = models.ForeignKey(
        "contas.Usuario", null=True, blank=True, on_delete=models.SET_NULL, related_name="lugares_criados"
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "lugares"
        constraints = [
            models.UniqueConstraint(
                fields=["fonte", "id_externo"],
                condition=~models.Q(id_externo=""),
                name="lugar_unico_por_fonte",
            )
        ]

    def __str__(self):
        return self.nome
