from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('generator', '0003_remove_generatedportfolio_updated_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='generatedportfolio',
            name='status',
            field=models.CharField(
                choices=[('processing', 'Processing'), ('completed', 'Completed'), ('error', 'Error')],
                default='completed',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='generatedportfolio',
            name='status_message',
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AlterField(
            model_name='generatedportfolio',
            name='generated_content',
            field=models.JSONField(default=dict),
        ),
    ]
