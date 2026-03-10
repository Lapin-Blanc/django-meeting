import json
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404
from django.utils import timezone
from django.forms import formset_factory

from .models import Poll, TimeSlot, Participant, Vote
from .forms import PollCreateForm, PollForm, ParticipantForm
from .tokens import generate_participant_token


ParticipantFormSet = formset_factory(ParticipantForm, extra=1, can_delete=False)


@login_required
def poll_list(request):
    polls = Poll.objects.filter(creator=request.user).prefetch_related('participants', 'time_slots')
    return render(request, 'polls/poll_list.html', {'polls': polls})


@login_required
def poll_create(request):
    if request.method == 'POST':
        poll_form = PollCreateForm(request.POST)
        participant_formset = ParticipantFormSet(request.POST, prefix='participants')

        if poll_form.is_valid() and participant_formset.is_valid():
            # Create poll
            poll = poll_form.save(commit=False)
            poll.creator = request.user
            poll.save()

            # Create time slots
            slots_data = poll_form.cleaned_data['time_slots_json']
            for slot in slots_data:
                TimeSlot.objects.create(
                    poll=poll,
                    start=slot['start'],
                    end=slot['end'],
                )

            # Create participants and send invitations
            emails_seen = set()
            for form in participant_formset:
                if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                    email = form.cleaned_data['email']
                    if email in emails_seen:
                        continue
                    emails_seen.add(email)
                    Participant.objects.create(
                        poll=poll,
                        name=form.cleaned_data['name'],
                        email=email,
                        token=generate_participant_token(),
                    )

            # Send invitation emails (imported here to avoid circular import)
            from .email import send_invitations
            send_invitations(poll, poll.participants.all(), request)

            messages.success(request, f'Sondage « {poll.title} » créé avec succès. Les invitations ont été envoyées.')
            return redirect('polls:poll_detail', pk=poll.pk)
    else:
        poll_form = PollCreateForm()
        participant_formset = ParticipantFormSet(prefix='participants')

    return render(request, 'polls/poll_create.html', {
        'poll_form': poll_form,
        'participant_formset': participant_formset,
    })


@login_required
def poll_detail(request, pk):
    poll = get_object_or_404(Poll, pk=pk, creator=request.user)
    time_slots = poll.time_slots.all().prefetch_related('votes__participant')
    participants = poll.participants.all().prefetch_related('votes')

    # Sort time slots by score descending
    slots_with_scores = sorted(time_slots, key=lambda s: s.score, reverse=True)

    # Build vote matrix: participant -> {slot_id: choice}
    vote_matrix = {}
    for participant in participants:
        vote_matrix[participant.id] = {
            str(v.time_slot_id): v.choice for v in participant.votes.all()
        }

    # Non-respondents
    non_respondents = [p for p in participants if not p.has_voted]

    # Best score
    best_score = slots_with_scores[0].score if slots_with_scores else 0

    return render(request, 'polls/poll_detail.html', {
        'poll': poll,
        'time_slots': slots_with_scores,
        'participants': participants,
        'vote_matrix': vote_matrix,
        'non_respondents': non_respondents,
        'best_score': best_score,
    })


@login_required
def poll_edit(request, pk):
    poll = get_object_or_404(Poll, pk=pk, creator=request.user)
    if not poll.is_active:
        messages.error(request, 'Ce sondage est clôturé et ne peut plus être modifié.')
        return redirect('polls:poll_detail', pk=poll.pk)

    existing_slots = list(poll.time_slots.values('id', 'start', 'end'))
    # Convert UUIDs and datetimes to strings for JSON serialization
    slots_json = json.dumps([{
        'id': str(s['id']),
        'start': s['start'].isoformat(),
        'end': s['end'].isoformat(),
    } for s in existing_slots])

    # Existing participants (convert UUIDs to strings for JSON serialization)
    existing_participants = [
        {'id': str(p.id), 'name': p.name, 'email': p.email}
        for p in poll.participants.all()
    ]

    if request.method == 'POST':
        poll_form = PollForm(request.POST, instance=poll)

        # Handle time slots
        slots_json_post = request.POST.get('time_slots_json', '[]')
        try:
            new_slots = json.loads(slots_json_post)
        except (json.JSONDecodeError, ValueError):
            new_slots = []

        # Handle participants
        new_participants_json = request.POST.get('participants_json', '[]')
        try:
            new_participants = json.loads(new_participants_json)
        except (json.JSONDecodeError, ValueError):
            new_participants = []

        remove_participants_json = request.POST.get('participants_remove_json', '[]')
        try:
            remove_participant_ids = json.loads(remove_participants_json)
        except (json.JSONDecodeError, ValueError):
            remove_participant_ids = []

        if poll_form.is_valid():
            from .forms import deadline_before_slots
            deadline = poll_form.cleaned_data.get('deadline')
            if new_slots and deadline and not deadline_before_slots(deadline, new_slots):
                poll_form.add_error('deadline', 'La date limite de vote doit être antérieure à tous les créneaux horaires.')
            else:
                poll_form.save()

                # Update time slots: delete removed, create new
                submitted_ids = {s.get('id') for s in new_slots if s.get('id')}
                existing_ids = {str(s['id']) for s in existing_slots}

                # Delete removed slots
                deleted_ids = existing_ids - submitted_ids
                if deleted_ids:
                    TimeSlot.objects.filter(id__in=deleted_ids, poll=poll).delete()

                # Create new slots (those without an ID)
                for slot in new_slots:
                    if not slot.get('id'):
                        TimeSlot.objects.create(
                            poll=poll,
                            start=slot['start'],
                            end=slot['end'],
                        )

                # Remove participants marked for deletion
                if remove_participant_ids:
                    Participant.objects.filter(id__in=remove_participant_ids, poll=poll).delete()

                # Handle new participants
                existing_emails = {p['email'] for p in existing_participants if str(p['id']) not in remove_participant_ids}
                new_invites = []
                for p in new_participants:
                    if p.get('email') and p['email'] not in existing_emails:
                        participant = Participant.objects.create(
                            poll=poll,
                            name=p.get('name', ''),
                            email=p['email'],
                            token=generate_participant_token(),
                        )
                        new_invites.append(participant)

                if new_invites:
                    from .email import send_invitations
                    send_invitations(poll, new_invites, request)

                messages.success(request, 'Sondage mis à jour avec succès.')
                return redirect('polls:poll_detail', pk=poll.pk)
    else:
        poll_form = PollForm(instance=poll)

    return render(request, 'polls/poll_edit.html', {
        'poll': poll,
        'poll_form': poll_form,
        'slots_json': slots_json,
        'existing_participants': json.dumps(existing_participants),
    })


@login_required
def poll_delete(request, pk):
    poll = get_object_or_404(Poll, pk=pk, creator=request.user)
    if request.method == 'POST':
        title = poll.title
        poll.delete()
        messages.success(request, f'Sondage « {title} » supprimé.')
        return redirect('polls:poll_list')
    return render(request, 'polls/poll_delete.html', {'poll': poll})


@login_required
def poll_close(request, pk):
    poll = get_object_or_404(Poll, pk=pk, creator=request.user)
    if request.method == 'POST':
        if not poll.is_closed:
            poll.is_closed = True
            poll.closed_at = timezone.now()
            poll.save()
            messages.success(request, 'Sondage clôturé.')
        return redirect('polls:poll_detail', pk=poll.pk)
    return redirect('polls:poll_detail', pk=poll.pk)


@login_required
def poll_choose_slot(request, pk, slot_id):
    poll = get_object_or_404(Poll, pk=pk, creator=request.user)
    slot = get_object_or_404(TimeSlot, pk=slot_id, poll=poll)
    if request.method == 'POST':
        poll.chosen_slot = slot
        poll.save()
        # Send final choice emails
        from .email import send_final_choice
        send_final_choice(poll, request)
        messages.success(request, f'Créneau retenu : {slot.start:%d/%m/%Y %H:%M}–{slot.end:%H:%M}. Les participants ont été notifiés.')
        return redirect('polls:poll_detail', pk=poll.pk)
    return redirect('polls:poll_detail', pk=poll.pk)


@login_required
def poll_remind(request, pk):
    poll = get_object_or_404(Poll, pk=pk, creator=request.user)
    if request.method == 'POST':
        non_respondents = poll.participants.filter(has_voted=False)
        if non_respondents.exists():
            from .email import send_reminders
            send_reminders(poll, non_respondents, request)
            messages.success(request, f'{non_respondents.count()} rappel(s) envoyé(s).')
        else:
            messages.info(request, 'Tous les participants ont déjà voté.')
        return redirect('polls:poll_detail', pk=poll.pk)
    return redirect('polls:poll_detail', pk=poll.pk)


# ============================================================
# Participant views
# ============================================================

def poll_vote(request, poll_id, token):
    """
    Display vote interface or read-only view for a participant.
    The token acts as authentication — no login required.
    """
    poll = get_object_or_404(Poll, pk=poll_id)
    participant = get_object_or_404(Participant, poll=poll, token=token)

    time_slots = poll.time_slots.all()

    # Build existing votes dict: {str(slot_id): choice}
    existing_votes = {str(v.time_slot_id): v.choice for v in participant.votes.all()}

    # Build time slots data for FullCalendar (JSON)
    slots_data = []
    for slot in time_slots:
        vote_choice = existing_votes.get(str(slot.id), '')
        slots_data.append({
            'id': str(slot.id),
            'start': slot.start.isoformat(),
            'end': slot.end.isoformat(),
            'choice': vote_choice,
        })

    # Compute summary (anonymized counts per slot)
    summary = []
    all_participants_count = poll.participants.count()
    for slot in time_slots:
        votes = list(slot.votes.all())
        yes = sum(1 for v in votes if v.choice == Vote.CHOICE_YES)
        maybe = sum(1 for v in votes if v.choice == Vote.CHOICE_MAYBE)
        no = sum(1 for v in votes if v.choice == Vote.CHOICE_NO)
        no_answer = all_participants_count - len(votes)
        summary.append({
            'slot': slot,
            'yes': yes,
            'maybe': maybe,
            'no': no,
            'no_answer': no_answer,
            'score': slot.score,
        })
    # Sort summary by score descending
    summary.sort(key=lambda x: x['score'], reverse=True)

    import json as _json
    context = {
        'poll': poll,
        'participant': participant,
        'time_slots': time_slots,
        'slots_json': _json.dumps(slots_data),
        'existing_votes': existing_votes,
        'summary': summary,
        'is_closed': not poll.is_active,
    }

    if not poll.is_active:
        return render(request, 'polls/poll_closed.html', context)
    return render(request, 'polls/poll_vote.html', context)


def poll_vote_submit(request, poll_id, token):
    """
    Submit votes for a participant (POST only).
    Accepts JSON body or form data with vote choices.
    """
    import json as _json
    from django.http import JsonResponse

    poll = get_object_or_404(Poll, pk=poll_id)
    participant = get_object_or_404(Participant, poll=poll, token=token)

    if not poll.is_active:
        return JsonResponse({'error': 'Ce sondage est clôturé.'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'Méthode non autorisée.'}, status=405)

    # Parse votes from JSON or form data
    try:
        body = _json.loads(request.body)
        votes_data = body.get('votes', {})
    except (ValueError, _json.JSONDecodeError):
        votes_data = {k: v for k, v in request.POST.items() if k.startswith('slot_')}
        votes_data = {k.replace('slot_', ''): v for k, v in votes_data.items()}

    valid_choices = {Vote.CHOICE_YES, Vote.CHOICE_MAYBE, Vote.CHOICE_NO}
    time_slot_ids = set(str(s.id) for s in poll.time_slots.all())

    for slot_id_str, choice in votes_data.items():
        if slot_id_str not in time_slot_ids or choice not in valid_choices:
            continue
        try:
            slot = poll.time_slots.get(id=slot_id_str)
        except Exception:
            continue
        Vote.objects.update_or_create(
            participant=participant,
            time_slot=slot,
            defaults={'choice': choice},
        )

    # Update participant status
    participant.has_voted = True
    participant.last_voted_at = timezone.now()
    participant.save()

    return JsonResponse({'status': 'ok', 'message': 'Votes enregistrés avec succès.'})


# ============================================================
# API
# ============================================================

def poll_summary_api(request, pk):
    """
    Returns anonymized vote counts and scores per time slot (JSON).
    """
    from django.http import JsonResponse
    poll = get_object_or_404(Poll, pk=pk)
    all_participants_count = poll.participants.count()
    data = []
    for slot in poll.time_slots.all():
        votes = list(slot.votes.all())
        yes = sum(1 for v in votes if v.choice == Vote.CHOICE_YES)
        maybe = sum(1 for v in votes if v.choice == Vote.CHOICE_MAYBE)
        no = sum(1 for v in votes if v.choice == Vote.CHOICE_NO)
        data.append({
            'id': str(slot.id),
            'start': slot.start.isoformat(),
            'end': slot.end.isoformat(),
            'yes': yes,
            'maybe': maybe,
            'no': no,
            'no_answer': all_participants_count - len(votes),
            'score': slot.score,
        })
    data.sort(key=lambda x: x['score'], reverse=True)
    return JsonResponse({'slots': data, 'total_participants': all_participants_count})
