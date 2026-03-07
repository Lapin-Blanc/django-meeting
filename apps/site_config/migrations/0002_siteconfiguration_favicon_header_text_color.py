from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('site_config', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='siteconfiguration',
            name='favicon',
            field=models.ImageField(
                blank=True,
                help_text='Icône onglet navigateur (PNG 32×32 recommandé). Si vide, le logo est utilisé.',
                null=True,
                upload_to='logos/',
                verbose_name='Favicon',
            ),
        ),
        migrations.AddField(
            model_name='siteconfiguration',
            name='header_text_color',
            field=models.CharField(
                default='#ffffff',
                help_text="Couleur du nom du site et des boutons dans la barre de navigation.",
                max_length=7,
                verbose_name="Couleur du texte de l'en-tête",
            ),
        ),
    ]
