from django.contrib import admin

from .models import Intencao, Salvo


@admin.register(Salvo)
class SalvoAdmin(admin.ModelAdmin):
    list_display = ["usuario", "tipo", "url", "lugar", "criado_em"]
    list_filter = ["origem", "tipo"]
    search_fields = ["usuario__email", "url", "perfil"]
    raw_id_fields = ["usuario", "lugar"]


@admin.register(Intencao)
class IntencaoAdmin(admin.ModelAdmin):
    list_display = ["salvo", "estado", "confianca", "frase", "lugar_sugerido", "lida_em"]
    list_filter = ["estado", "confianca", "versao_prompt"]
    search_fields = ["salvo__usuario__email", "frase", "lugar_nome"]
    raw_id_fields = ["salvo", "lugar_sugerido"]
    filter_horizontal = ["tags"]
