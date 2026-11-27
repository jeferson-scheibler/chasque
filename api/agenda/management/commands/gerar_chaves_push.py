import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.core.management.base import BaseCommand


def b64(dados):
    return base64.urlsafe_b64encode(dados).rstrip(b"=").decode()


class Command(BaseCommand):
    help = "Gera um par de chaves VAPID para o Web Push. Copie as linhas para o .env."

    def handle(self, **_):
        privada = ec.generate_private_key(ec.SECP256R1())
        bruta = privada.private_numbers().private_value.to_bytes(32, "big")
        publica = privada.public_key().public_bytes(
            serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
        )
        self.stdout.write(f"VAPID_PUBLICA={b64(publica)}")
        self.stdout.write(f"VAPID_PRIVADA={b64(bruta)}")
