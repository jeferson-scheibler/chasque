from django.contrib import admin

from .models import Salvo


@admin.register(Salvo)
class SalvoAdmin(admin.ModelAdmin):
    list_display = ["usuario", "tipo", "url", "lugar", "criado_em"]
    list_filter = ["origem", "tipo"]
    search_fields = ["usuario__email", "url", "perfil"]
    raw_id_fields = ["usuario", "lugar"]
