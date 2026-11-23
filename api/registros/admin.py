from django.contrib import admin

from .models import PesoGosto, PreferenciaDeclarada, Registro


@admin.register(Registro)
class RegistroAdmin(admin.ModelAdmin):
    list_display = ["usuario", "lugar", "visitado_em", "ocasiao", "nota", "privado"]
    list_filter = ["ocasiao", "nota", "privado"]
    search_fields = ["usuario__email", "lugar__nome"]
    raw_id_fields = ["usuario", "lugar"]
    filter_horizontal = ["tags"]


@admin.register(PreferenciaDeclarada)
class PreferenciaDeclaradaAdmin(admin.ModelAdmin):
    list_display = ["usuario", "tag", "criado_em"]
    raw_id_fields = ["usuario"]


@admin.register(PesoGosto)
class PesoGostoAdmin(admin.ModelAdmin):
    list_display = ["usuario", "tag", "ocasiao", "peso", "atualizado_em"]
    list_filter = ["ocasiao"]
    raw_id_fields = ["usuario"]
