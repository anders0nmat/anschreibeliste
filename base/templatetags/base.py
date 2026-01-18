from django import template
from django.http import HttpRequest

from ..nav import navbar

register = template.Library()

@register.inclusion_tag("linktree.html", takes_context=True)
def link_tree(context):
    request: HttpRequest = context["request"]
    links = (item.for_request(request) for item in navbar)
    links = (item for item in links if item)
    
    links = list(links)
    return { "links": links }

@register.simple_tag(takes_context=True)
def link_title(context):
    request: HttpRequest = context["request"]
    links = (item.for_request(request) for item in navbar)
    links = (item for item in links if item)

    for item in links:
        if item.active:
            return item.title

    return ''
