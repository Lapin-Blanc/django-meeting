from django.urls import path
from . import views

app_name = 'polls'

urlpatterns = [
    # Creator views
    path('', views.poll_list, name='poll_list'),
    path('poll/create/', views.poll_create, name='poll_create'),
    path('poll/<uuid:pk>/', views.poll_detail, name='poll_detail'),
    path('poll/<uuid:pk>/edit/', views.poll_edit, name='poll_edit'),
    path('poll/<uuid:pk>/close/', views.poll_close, name='poll_close'),
    path('poll/<uuid:pk>/choose/<uuid:slot_id>/', views.poll_choose_slot, name='poll_choose_slot'),
    path('poll/<uuid:pk>/remind/', views.poll_remind, name='poll_remind'),
    path('poll/<uuid:pk>/delete/', views.poll_delete, name='poll_delete'),
    # Participant views (step 7)
    path('poll/<uuid:poll_id>/vote/<str:token>/', views.poll_vote, name='poll_vote'),
    path('poll/<uuid:poll_id>/vote/<str:token>/submit/', views.poll_vote_submit, name='poll_vote_submit'),
    # API (step 8)
    path('api/poll/<uuid:pk>/summary/', views.poll_summary_api, name='poll_summary_api'),
]
