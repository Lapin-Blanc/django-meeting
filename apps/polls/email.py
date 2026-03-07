"""
Dynamic email sending for django-meeting.

Reads SMTP settings from SiteConfiguration at each send, creating a live
connection. Falls back to Django console backend if SMTP is not configured.
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from django.core.mail import get_connection, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


def _get_smtp_connection():
    """
    Create a Django email connection using SiteConfiguration SMTP settings.
    Returns None if SMTP is not configured (caller should use console backend).
    """
    from apps.site_config.models import SiteConfiguration
    config = SiteConfiguration.get_solo()

    if not config.smtp_host or not config.smtp_from_email:
        return None, None

    connection = get_connection(
        backend='django.core.mail.backends.smtp.EmailBackend',
        host=config.smtp_host,
        port=config.smtp_port,
        username=config.smtp_username,
        password=config.smtp_password,
        use_tls=config.smtp_use_tls,
        fail_silently=False,
    )
    return connection, config.smtp_from_email


def _send_email(subject, to_email, html_content, text_content, from_email=None):
    """
    Send a single email. Uses SiteConfiguration SMTP or falls back to
    Django console backend.
    """
    try:
        connection, smtp_from = _get_smtp_connection()
    except Exception as exc:
        logger.warning('Could not load SiteConfiguration for SMTP: %s', exc)
        connection, smtp_from = None, None

    if connection is None:
        # Fallback: use Django's configured backend (console in dev)
        from django.core.mail import send_mail
        from django.conf import settings
        send_mail(
            subject=subject,
            message=text_content,
            from_email=from_email or settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            html_message=html_content,
            fail_silently=True,
        )
        return

    from_email = smtp_from or from_email
    try:
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=[to_email],
            connection=connection,
        )
        email.attach_alternative(html_content, 'text/html')
        email.send()
    except smtplib.SMTPException as exc:
        logger.error('SMTP error sending to %s: %s', to_email, exc)
    except OSError as exc:
        logger.error('Connection error sending to %s: %s', to_email, exc)


def _render_email(template_name, context):
    """Render HTML and plain-text versions of an email template."""
    html = render_to_string(f'emails/{template_name}.html', context)
    txt = render_to_string(f'emails/{template_name}.txt', context)
    return html, txt


def send_invitations(poll, participants, request):
    """Send invitation emails to a list of participants."""
    from apps.site_config.models import SiteConfiguration
    site_config = SiteConfiguration.get_solo()
    base_url = request.build_absolute_uri('/').rstrip('/')

    for participant in participants:
        vote_url = f"{base_url}/poll/{poll.id}/vote/{participant.token}/"
        context = {
            'poll': poll,
            'participant': participant,
            'vote_url': vote_url,
            'site_config': site_config,
        }
        html, txt = _render_email('invitation', context)
        subject = f"Invitation à voter : {poll.title}"
        _send_email(subject, participant.email, html, txt)
        logger.info('Invitation sent to %s for poll %s', participant.email, poll.id)


def send_reminders(poll, participants, request):
    """Send reminder emails to participants who haven't voted yet."""
    from apps.site_config.models import SiteConfiguration
    site_config = SiteConfiguration.get_solo()
    base_url = request.build_absolute_uri('/').rstrip('/')

    for participant in participants:
        vote_url = f"{base_url}/poll/{poll.id}/vote/{participant.token}/"
        context = {
            'poll': poll,
            'participant': participant,
            'vote_url': vote_url,
            'site_config': site_config,
        }
        html, txt = _render_email('reminder', context)
        subject = f"Rappel : votez pour {poll.title}"
        _send_email(subject, participant.email, html, txt)
        logger.info('Reminder sent to %s for poll %s', participant.email, poll.id)


def send_final_choice(poll, request):
    """Send final choice notification to all participants."""
    from apps.site_config.models import SiteConfiguration
    site_config = SiteConfiguration.get_solo()
    base_url = request.build_absolute_uri('/').rstrip('/')

    for participant in poll.participants.all():
        vote_url = f"{base_url}/poll/{poll.id}/vote/{participant.token}/"
        context = {
            'poll': poll,
            'participant': participant,
            'chosen_slot': poll.chosen_slot,
            'vote_url': vote_url,
            'site_config': site_config,
        }
        html, txt = _render_email('final_choice', context)
        subject = f"Créneau retenu pour : {poll.title}"
        _send_email(subject, participant.email, html, txt)
        logger.info('Final choice notification sent to %s for poll %s', participant.email, poll.id)
