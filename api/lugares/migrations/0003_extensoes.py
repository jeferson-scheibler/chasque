from django.contrib.postgres.operations import TrigramExtension, UnaccentExtension
from django.db import migrations


class Migration(migrations.Migration):
    """Busca de lugares sem acento (unaccent) e tolerante a erro de digitação (pg_trgm)."""

    dependencies = [("lugares", "0002_tags_iniciais")]
    operations = [UnaccentExtension(), TrigramExtension()]
