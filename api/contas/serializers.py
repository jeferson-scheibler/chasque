from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers

from .models import Usuario, UsuarioManager


class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ["id", "email", "nome", "cidade_base", "contribuir_motivos", "usar_ia", "date_joined"]
        read_only_fields = ["id", "email", "date_joined"]


class CadastroSerializer(serializers.Serializer):
    email = serializers.EmailField()
    nome = serializers.CharField(max_length=120)
    senha = serializers.CharField(write_only=True, trim_whitespace=False)
    aceita_termos = serializers.BooleanField()

    def validate_email(self, valor):
        valor = UsuarioManager.normalizar_email(valor)
        if Usuario.objects.filter(email=valor).exists():
            raise serializers.ValidationError("Já existe uma conta com este e-mail.")
        return valor

    def validate_aceita_termos(self, valor):
        if not valor:
            raise serializers.ValidationError("É preciso aceitar os termos de uso e a política de privacidade.")
        return valor

    def validate(self, attrs):
        provisorio = Usuario(email=attrs["email"], nome=attrs["nome"])
        try:
            validate_password(attrs["senha"], user=provisorio)
        except Exception as erro:
            raise serializers.ValidationError({"senha": list(erro.messages)})
        return attrs

    def create(self, dados):
        return Usuario.objects.create_user(
            email=dados["email"],
            password=dados["senha"],
            nome=dados["nome"],
            termos_aceitos_em=timezone.now(),
            versao_termos=settings.VERSAO_TERMOS,
        )


class EntrarSerializer(serializers.Serializer):
    email = serializers.EmailField()
    senha = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        usuario = authenticate(
            request=self.context.get("request"),
            username=UsuarioManager.normalizar_email(attrs["email"]),
            password=attrs["senha"],
        )
        # None quando falha. A view responde 401 com mensagem unica,
        # que nao revela se o e-mail existe.
        attrs["usuario"] = usuario
        return attrs
