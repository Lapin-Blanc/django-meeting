from django.contrib import admin
from solo.admin import SingletonModelAdmin
from .models import SiteConfiguration


@admin.register(SiteConfiguration)
class SiteConfigurationAdmin(SingletonModelAdmin):
    fieldsets = (
        ('Identité du site', {
            'fields': ('site_name', 'logo', 'primary_color', 'secondary_color'),
        }),
        ('Configuration SMTP', {
            'fields': (
                'smtp_host', 'smtp_port', 'smtp_use_tls',
                'smtp_username', 'smtp_password', 'smtp_from_email',
            ),
            'description': (
                "Si aucun serveur SMTP n'est configuré, les emails seront "
                "affichés dans la console en mode développement."
            ),
        }),
        ('Rétention des données', {
            'fields': ('retention_days',),
        }),
    )
