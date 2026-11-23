from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin

from .models import Cidade, Lugar, MotivoComunidade, Tag


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ["nome", "slug", "grupo"]
    list_filter = ["grupo"]
    search_fields = ["nome", "slug"]


@admin.register(Lugar)
class LugarAdmin(GISModelAdmin):
    list_display = ["nome", "cidade", "categoria", "fonte", "aproximado", "verificado", "atualizado_em"]
    list_filter = ["fonte", "verificado", "aproximado", "cidade"]
    search_fields = ["nome", "endereco", "id_externo"]
    filter_horizontal = ["tags"]
    raw_id_fields = ["criado_por"]


@admin.register(Cidade)
class CidadeAdmin(GISModelAdmin):
    list_display = ["nome", "id_externo"]
    search_fields = ["nome"]


@admin.register(MotivoComunidade)
class MotivoComunidadeAdmin(admin.ModelAdmin):
    list_display = ["lugar", "tag", "pessoas", "atualizado_em"]
    list_filter = ["tag"]
    search_fields = ["lugar__nome"]
    raw_id_fields = ["lugar"]
