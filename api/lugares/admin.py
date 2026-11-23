from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin

from .models import Lugar, Tag


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ["nome", "slug", "grupo"]
    list_filter = ["grupo"]
    search_fields = ["nome", "slug"]


@admin.register(Lugar)
class LugarAdmin(GISModelAdmin):
    list_display = ["nome", "categoria", "fonte", "verificado", "atualizado_em"]
    list_filter = ["fonte", "verificado", "categoria"]
    search_fields = ["nome", "endereco", "id_externo"]
    filter_horizontal = ["tags"]
