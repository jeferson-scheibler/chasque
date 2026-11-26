from django.db import migrations


def criar(apps, _schema):
    Tag = apps.get_model("lugares", "Tag")
    Tag.objects.update_or_create(slug="cabe-grupo", defaults={"nome": "Cabe muita gente", "grupo": "ambiente"})


def remover(apps, _schema):
    apps.get_model("lugares", "Tag").objects.filter(slug="cabe-grupo").delete()


class Migration(migrations.Migration):
    dependencies = [("lugares", "0008_lugar_capacidade")]
    operations = [migrations.RunPython(criar, remover)]
