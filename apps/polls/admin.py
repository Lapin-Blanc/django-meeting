from django.contrib import admin
from .models import Poll, TimeSlot, Participant, Vote


class TimeSlotInline(admin.TabularInline):
    model = TimeSlot
    extra = 0


class ParticipantInline(admin.TabularInline):
    model = Participant
    extra = 0
    fields = ('name', 'email', 'has_voted', 'invited_at')
    readonly_fields = ('invited_at',)


@admin.register(Poll)
class PollAdmin(admin.ModelAdmin):
    list_display = ('title', 'creator', 'deadline', 'is_closed', 'poll_is_active', 'created_at')
    list_filter = ('is_closed', 'creator')
    search_fields = ('title', 'creator__username')
    inlines = [TimeSlotInline, ParticipantInline]
    readonly_fields = ('created_at', 'closed_at')

    @admin.display(boolean=True, description='Actif')
    def poll_is_active(self, obj):
        return obj.is_active


@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ('poll', 'start', 'end')
    list_filter = ('poll',)


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'poll', 'has_voted', 'invited_at')
    list_filter = ('has_voted', 'poll')
    search_fields = ('name', 'email')
    readonly_fields = ('token', 'invited_at')


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ('participant', 'time_slot', 'choice', 'updated_at')
    list_filter = ('choice',)
