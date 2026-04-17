from django import template

register = template.Library()

@register.filter
def get(d, key):
    """Get a value from a dictionary by key."""
    if isinstance(d, dict):
        return d.get(key, '')
    return ''