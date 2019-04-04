from django import template

register = template.Library()


@register.filter(name='key')
def key(dict, key):
    return dict.get(key)
