from django import template
from django.utils.translation import get_language

from helpers.models import HelpContent

register = template.Library()


@register.inclusion_tag("includes/help_modal.html", takes_context=True)
def help_modal(context, key):
    lang = get_language() or "en"
    content = (
        HelpContent.objects.filter(key=key, language=lang).first()
        or HelpContent.objects.filter(key=key, language=lang[:2]).first()
        or HelpContent.objects.filter(key=key, language="en").first()
    )
    modal_id = key.replace(".", "-")

    # Check if the current user has dismissed this helper
    dismissed = False
    request = context.get("request")
    if request and hasattr(request, "user") and request.user.is_authenticated:
        dismissed_helpers = getattr(request.user, "dismissed_helpers", None)
        if isinstance(dismissed_helpers, list) and key in dismissed_helpers:
            dismissed = True

    return {"help_content": content, "modal_id": modal_id, "helper_key": key, "dismissed": dismissed}
