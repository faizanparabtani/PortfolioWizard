from django.db import migrations


TEMPLATES = [
    {
        "name": "Minimal",
        "description": "A clean, light-themed portfolio. Simple typography, card-based projects, and a smooth layout that lets your work speak for itself.",
        "template_folder": "portfolios/minimal",
        "thumbnail": "",
        "is_active": True,
    },
    {
        "name": "Modern Dark",
        "description": "A bold dark-themed portfolio with a purple accent and subtle glow effects. Great for developers and designers who want to stand out.",
        "template_folder": "portfolios/modern",
        "thumbnail": "",
        "is_active": True,
    },
]


def seed_templates(apps, schema_editor):
    PortfolioTemplate = apps.get_model("generator", "PortfolioTemplate")
    for data in TEMPLATES:
        PortfolioTemplate.objects.get_or_create(
            template_folder=data["template_folder"],
            defaults=data,
        )


def remove_templates(apps, schema_editor):
    PortfolioTemplate = apps.get_model("generator", "PortfolioTemplate")
    folders = [t["template_folder"] for t in TEMPLATES]
    PortfolioTemplate.objects.filter(template_folder__in=folders).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("generator", "0006_remove_generatedportfolio_netlify_deploy_id_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_templates, remove_templates),
    ]
