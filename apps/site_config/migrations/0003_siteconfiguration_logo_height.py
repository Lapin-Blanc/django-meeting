from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('site_config', '0002_siteconfiguration_favicon_header_text_color'),
    ]

    operations = [
        migrations.AddField(
            model_name='siteconfiguration',
            name='logo_height',
            field=models.PositiveIntegerField(
                default=70,
                help_text='Hauteur du logo dans la barre de navigation, en pixels.',
                verbose_name='Hauteur du logo (px)',
            ),
        ),
    ]
