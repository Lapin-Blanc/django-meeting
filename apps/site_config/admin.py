from django import forms
from django.contrib import admin
from django.utils.html import format_html
from solo.admin import SingletonModelAdmin
from .models import SiteConfiguration


COLOR_INPUT = {'type': 'color', 'style': 'width:80px; height:40px; padding:2px; cursor:pointer;'}


class SiteConfigurationForm(forms.ModelForm):
    primary_color = forms.CharField(
        label='Couleur primaire',
        widget=forms.TextInput(attrs=COLOR_INPUT),
        help_text='Utilisée pour les boutons principaux et accents.',
    )
    secondary_color = forms.CharField(
        label='Couleur secondaire',
        widget=forms.TextInput(attrs=COLOR_INPUT),
        help_text='Utilisée pour les accents secondaires.',
    )
    header_text_color = forms.CharField(
        label="Couleur du texte de l'en-tête",
        widget=forms.TextInput(attrs=COLOR_INPUT),
        help_text='Couleur du nom du site et des boutons dans la barre de navigation.',
    )

    class Meta:
        model = SiteConfiguration
        fields = '__all__'


@admin.register(SiteConfiguration)
class SiteConfigurationAdmin(SingletonModelAdmin):
    form = SiteConfigurationForm
    change_form_template = 'admin/site_config/siteconfiguration/change_form.html'
    readonly_fields = ('logo_preview',)

    fieldsets = (
        ('Identité du site', {
            'fields': ('site_name', 'logo_preview', 'logo', 'logo_height', 'favicon', 'primary_color', 'secondary_color', 'header_text_color'),
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

    @admin.display(description='Logo actuel')
    def logo_preview(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" style="max-height:120px; max-width:400px; '
                'object-fit:contain; border:1px solid #e5e7eb; '
                'border-radius:6px; padding:8px; background:#fff;">',
                obj.logo.url,
            )
        return '— Aucun logo défini —'
