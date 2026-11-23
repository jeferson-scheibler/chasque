from django.db import migrations

# Primeiro vocabulario de motivos. Ajustar com o que aparecer nos testes com usuarios.
TAGS = {
    "ambiente": [
        ("silencioso", "Silencioso"),
        ("animado", "Animado"),
        ("aconchegante", "Aconchegante"),
        ("ao-ar-livre", "Ao ar livre"),
        ("vista-bonita", "Vista bonita"),
        ("historico", "História do lugar"),
    ],
    "preco": [
        ("economico", "Econômico"),
        ("preco-justo", "Preço justo"),
        ("vale-o-investimento", "Vale o investimento"),
    ],
    "comida": [
        ("comida-caseira", "Comida caseira"),
        ("cafe-colonial", "Café colonial"),
        ("cafe-especial", "Café especial"),
        ("cerveja-artesanal", "Cerveja artesanal"),
        ("vinho", "Vinho"),
        ("churrasco", "Churrasco"),
        ("doces", "Doces"),
        ("vegetariano", "Opções vegetarianas"),
    ],
    "servico": [
        ("atendimento-atencioso", "Atendimento atencioso"),
        ("rapido", "Rápido"),
        ("aceita-pet", "Aceita pet"),
        ("acessivel", "Acessível"),
        ("bom-para-criancas", "Bom para crianças"),
    ],
    "experiencia": [
        ("cultura-local", "Cultura local"),
        ("natureza", "Natureza"),
        ("arte", "Arte"),
        ("musica-ao-vivo", "Música ao vivo"),
        ("produtor-local", "Produtor local"),
    ],
}


def criar(apps, _schema):
    Tag = apps.get_model("lugares", "Tag")
    for grupo, itens in TAGS.items():
        for slug, nome in itens:
            Tag.objects.update_or_create(slug=slug, defaults={"nome": nome, "grupo": grupo})


def remover(apps, _schema):
    Tag = apps.get_model("lugares", "Tag")
    slugs = [slug for itens in TAGS.values() for slug, _ in itens]
    Tag.objects.filter(slug__in=slugs).delete()


class Migration(migrations.Migration):
    dependencies = [("lugares", "0001_initial")]
    operations = [migrations.RunPython(criar, remover)]
