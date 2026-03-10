import json
from django import forms
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from .models import Poll, Participant


def deadline_before_slots(deadline, slots):
    """Return True if deadline is strictly before all slot start times."""
    starts = []
    for s in slots:
        start_str = s.get('start')
        if start_str:
            dt = parse_datetime(start_str)
            if dt is not None:
                if timezone.is_naive(dt):
                    dt = timezone.make_aware(dt)
                starts.append(dt)
    return not starts or deadline < min(starts)


class PollForm(forms.ModelForm):
    class Meta:
        model = Poll
        fields = ['title', 'description', 'location', 'deadline']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Titre du sondage'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Description (optionnel)'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Lieu (optionnel)'}),
            'deadline': forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'
            ),
        }
        labels = {
            'title': 'Titre',
            'description': 'Description',
            'location': 'Lieu',
            'deadline': 'Date limite de vote',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['deadline'].input_formats = ['%Y-%m-%dT%H:%M']
        if self.instance and self.instance.pk and self.instance.deadline:
            self.initial['deadline'] = self.instance.deadline.strftime('%Y-%m-%dT%H:%M')

    def clean_deadline(self):
        deadline = self.cleaned_data.get('deadline')
        if deadline and deadline <= timezone.now():
            raise forms.ValidationError('La date limite doit être dans le futur.')
        return deadline


class TimeSlotsField(forms.CharField):
    """Hidden field that receives JSON-encoded time slots from the calendar."""
    widget = forms.HiddenInput

    def clean(self, value):
        value = super().clean(value)
        if not value:
            raise forms.ValidationError('Veuillez définir au moins un créneau horaire.')
        try:
            slots = json.loads(value)
        except (json.JSONDecodeError, ValueError):
            raise forms.ValidationError('Format de créneaux invalide.')
        if not isinstance(slots, list) or len(slots) == 0:
            raise forms.ValidationError('Veuillez définir au moins un créneau horaire.')
        return slots


class PollCreateForm(PollForm):
    time_slots_json = TimeSlotsField(required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Order fields
        self.fields = {
            'title': self.fields['title'],
            'description': self.fields['description'],
            'location': self.fields['location'],
            'deadline': self.fields['deadline'],
            'time_slots_json': self.fields['time_slots_json'],
        }

    def clean(self):
        cleaned_data = super().clean()
        deadline = cleaned_data.get('deadline')
        slots = cleaned_data.get('time_slots_json')
        if deadline and slots and not deadline_before_slots(deadline, slots):
            self.add_error('deadline', 'La date limite de vote doit être antérieure à tous les créneaux horaires.')
        return cleaned_data


class ParticipantFormSet(forms.BaseFormSet):
    pass


class ParticipantForm(forms.Form):
    name = forms.CharField(
        label='Nom',
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom du participant'})
    )
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@exemple.com'})
    )
