import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class PollsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.polls'
    verbose_name = 'Sondages'

    def ready(self):
        self._start_scheduler()

    def _start_scheduler(self):
        """Register and start APScheduler jobs."""
        import sys
        # Don't run scheduler in management commands (except runserver)
        # and don't run it twice (APScheduler would raise)
        skip_commands = {'test', 'migrate', 'makemigrations', 'check', 'collectstatic',
                         'shell', 'dbshell', 'createsuperuser', 'changepassword'}
        if any(cmd in sys.argv for cmd in skip_commands):
            return

        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.cron import CronTrigger
            from apscheduler.triggers.interval import IntervalTrigger
            from django_apscheduler.jobstores import DjangoJobStore
            from django_apscheduler.models import DjangoJobExecution

            from .tasks import close_expired_polls, purge_old_polls

            scheduler = BackgroundScheduler(timezone='Europe/Brussels')
            scheduler.add_jobstore(DjangoJobStore(), 'default')

            scheduler.add_job(
                close_expired_polls,
                trigger=IntervalTrigger(minutes=5),
                id='close_expired_polls',
                name='Clôture automatique des sondages expirés',
                replace_existing=True,
            )

            scheduler.add_job(
                purge_old_polls,
                trigger=CronTrigger(hour=3, minute=0),
                id='purge_old_polls',
                name='Suppression des anciens sondages',
                replace_existing=True,
            )

            scheduler.start()
            logger.info('APScheduler started: close_expired_polls (5min), purge_old_polls (3h daily)')

        except Exception as exc:
            logger.warning('Could not start APScheduler: %s', exc)
