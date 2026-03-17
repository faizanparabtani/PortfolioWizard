from django import template
from django.forms import Textarea

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Allow dict lookup by variable key in templates: {{ dict|get_item:key }}"""
    return dictionary.get(key, 0)


@register.filter
def is_textarea(field):
    """Return True if a BoundField's widget is a Textarea."""
    return isinstance(field.field.widget, Textarea)
