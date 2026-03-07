from .models import SiteConfiguration


def site_configuration(request):
    """Injecte la configuration du site dans tous les templates."""
    config = SiteConfiguration.get_solo()
    return {'site_config': config}
