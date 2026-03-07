"""
Scheduled tasks for django-meeting using django-apscheduler.

Registered in PollsConfig.ready() via scheduler.py.
"""

import logging
from django.utils import timezone

logger = logging.getLogger(__name__)


def close_expired_polls():
    """
    Close polls whose deadline has passed and are not yet closed.
    Runs every 5 minutes.
    """
    from .models import Poll
    now = timezone.now()
    expired = Poll.objects.filter(is_closed=False, deadline__lt=now)
    count = expired.count()
    if count:
        expired.update(is_closed=True, closed_at=now)
        logger.info('close_expired_polls: closed %d poll(s)', count)


def purge_old_polls():
    """
    Delete closed polls whose retention period has expired.
    Retention days is read from SiteConfiguration.
    Runs once per day at 3:00 AM.
    """
    from .models import Poll
    from apps.site_config.models import SiteConfiguration
    from datetime import timedelta

    config = SiteConfiguration.get_solo()
    retention_days = config.retention_days
    cutoff = timezone.now() - timedelta(days=retention_days)

    to_delete = Poll.objects.filter(is_closed=True, closed_at__lt=cutoff)
    count = to_delete.count()
    if count:
        to_delete.delete()
        logger.info('purge_old_polls: deleted %d poll(s) older than %d days', count, retention_days)
