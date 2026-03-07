from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Get item from a dictionary by key."""
    if dictionary is None:
        return None
    return dictionary.get(key)


@register.simple_tag
def get_vote(vote_matrix, participant_id, slot_id):
    """Get vote choice for a participant and slot."""
    participant_votes = vote_matrix.get(participant_id, {})
    return participant_votes.get(str(slot_id), '')
