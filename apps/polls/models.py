import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Poll(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='polls', verbose_name='Créateur')
    title = models.CharField('Titre', max_length=200)
    description = models.TextField('Description', blank=True)
    location = models.CharField('Lieu', max_length=200, blank=True)
    deadline = models.DateTimeField('Date limite de vote')
    is_closed = models.BooleanField('Clôturé', default=False)
    chosen_slot = models.ForeignKey(
        'TimeSlot',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chosen_for_polls',
        verbose_name='Créneau retenu'
    )
    created_at = models.DateTimeField('Créé le', auto_now_add=True)
    closed_at = models.DateTimeField('Clôturé le', null=True, blank=True)

    class Meta:
        verbose_name = 'Sondage'
        verbose_name_plural = 'Sondages'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def is_active(self):
        return not self.is_closed and self.deadline > timezone.now()


class TimeSlot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name='time_slots', verbose_name='Sondage')
    start = models.DateTimeField('Début')
    end = models.DateTimeField('Fin')

    class Meta:
        verbose_name = 'Créneau horaire'
        verbose_name_plural = 'Créneaux horaires'
        ordering = ['start']

    def __str__(self):
        return f"{self.poll.title} — {self.start:%d/%m/%Y %H:%M}–{self.end:%H:%M}"

    @property
    def score(self):
        """Score pondéré : yes=1.0, maybe=0.5, no=0.0"""
        weights = {'yes': 1.0, 'maybe': 0.5, 'no': 0.0}
        total = sum(weights.get(v.choice, 0.0) for v in self.votes.all())
        return total


class Participant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name='participants', verbose_name='Sondage')
    name = models.CharField('Nom', max_length=100)
    email = models.EmailField('Email')
    token = models.CharField('Token', max_length=64, unique=True)
    has_voted = models.BooleanField('A voté', default=False)
    invited_at = models.DateTimeField('Invité le', auto_now_add=True)
    last_voted_at = models.DateTimeField('Dernier vote le', null=True, blank=True)

    class Meta:
        verbose_name = 'Participant'
        verbose_name_plural = 'Participants'
        unique_together = [('poll', 'email')]
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.email})"


class Vote(models.Model):
    CHOICE_YES = 'yes'
    CHOICE_MAYBE = 'maybe'
    CHOICE_NO = 'no'
    CHOICE_CHOICES = [
        (CHOICE_YES, 'Oui'),
        (CHOICE_MAYBE, 'Peut-être'),
        (CHOICE_NO, 'Non'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='votes', verbose_name='Participant')
    time_slot = models.ForeignKey(TimeSlot, on_delete=models.CASCADE, related_name='votes', verbose_name='Créneau')
    choice = models.CharField('Choix', max_length=10, choices=CHOICE_CHOICES)
    updated_at = models.DateTimeField('Mis à jour le', auto_now=True)

    class Meta:
        verbose_name = 'Vote'
        verbose_name_plural = 'Votes'
        unique_together = [('participant', 'time_slot')]

    def __str__(self):
        return f"{self.participant.name} — {self.time_slot} : {self.get_choice_display()}"
