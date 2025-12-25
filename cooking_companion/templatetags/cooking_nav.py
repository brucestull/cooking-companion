from __future__ import annotations

from django import template
from django.urls import NoReverseMatch, reverse

register = template.Library()


@register.simple_tag(takes_context=True)
def cc_nav_active(context, url_name: str) -> str:
    request = context.get("request")
    if not request:
        return ""
    try:
        url = reverse(url_name)
    except NoReverseMatch:
        return ""
    if request.path == url or request.path.startswith(url):
        return "active"
    return ""


@register.simple_tag
def cc_target_url(model_key: str, obj_pk: int) -> str:
    return reverse("cooking_companion:target-detail", kwargs={"model_key": model_key, "pk": obj_pk})
