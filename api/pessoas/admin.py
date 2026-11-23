from django.contrib import admin

from .models import Confianca, Convite


@admin.register(Confianca)
class ConfiancaAdmin(admin.ModelAdmin):
    list_display = ["seguidor", "seguido", "estado", "criado_em", "aceito_em"]
    list_filter = ["estado"]
    raw_id_fields = ["seguidor", "seguido"]


@admin.register(Convite)
class ConviteAdmin(admin.ModelAdmin):
    list_display = ["usuario", "criado_em"]
    raw_id_fields = ["usuario"]
