from django.db import models
from solo.models import SingletonModel


class SiteConfiguration(SingletonModel):
    site_name = models.CharField('Nom du site', max_length=100, default='django-meeting')
    logo = models.ImageField('Logo', upload_to='logos/', blank=True, null=True)
    logo_height = models.PositiveIntegerField('Hauteur du logo (px)', default=70,
                                              help_text='Hauteur du logo dans la barre de navigation, en pixels.')
    favicon = models.ImageField('Favicon', upload_to='logos/', blank=True, null=True,
                                help_text='Icône onglet navigateur (PNG 32×32 recommandé). Si vide, le logo est utilisé.')
    primary_color = models.CharField('Couleur primaire', max_length=7, default='#2563eb')
    secondary_color = models.CharField('Couleur secondaire', max_length=7, default='#1e40af')
    header_text_color = models.CharField('Couleur du texte de l\'en-tête', max_length=7, default='#ffffff',
                                         help_text='Couleur du nom du site et des boutons dans la barre de navigation.')

    # SMTP
    smtp_host = models.CharField('Serveur SMTP', max_length=255, blank=True)
    smtp_port = models.PositiveIntegerField('Port SMTP', default=587)
    smtp_use_tls = models.BooleanField('TLS activé', default=True)
    smtp_username = models.CharField('Identifiant SMTP', max_length=255, blank=True)
    smtp_password = models.CharField('Mot de passe SMTP', max_length=255, blank=True)
    smtp_from_email = models.EmailField('Email expéditeur', blank=True)

    retention_days = models.PositiveIntegerField(
        'Rétention (jours)',
        default=90,
        help_text='Nombre de jours avant suppression automatique après clôture'
    )

    class Meta:
        verbose_name = 'Configuration du site'

    def __str__(self):
        return self.site_name
