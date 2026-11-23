from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    ordering = ["email"]
    list_display = ["email", "nome", "cidade_base", "is_staff", "date_joined"]
    search_fields = ["email", "nome"]
    readonly_fields = ["termos_aceitos_em", "versao_termos", "last_login", "date_joined"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Perfil", {"fields": ("nome", "cidade_base")}),
        ("Consentimento", {"fields": ("termos_aceitos_em", "versao_termos")}),
        ("Permissões", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Datas", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "nome", "password1", "password2")}),
    )
