import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('generator', '0004_generatedportfolio_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='generatedportfolio',
            name='public_slug',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
