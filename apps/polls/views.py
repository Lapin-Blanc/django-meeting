from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def poll_list(request):
    """Liste des sondages du créateur — implémentée à l'étape 5."""
    return render(request, 'polls/poll_list.html', {})
