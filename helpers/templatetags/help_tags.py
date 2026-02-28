from django import template
from django.utils.translation import get_language

from helpers.models import HelpContent

register = template.Library()


@register.inclusion_tag("includes/help_modal.html")
def help_modal(key):
    lang = get_language() or "fr"
    content = (
        HelpContent.objects.filter(key=key, language=lang).first()
        or HelpContent.objects.filter(key=key, language=lang[:2]).first()
        or HelpContent.objects.filter(key=key, language="fr").first()
    )
    modal_id = key.replace(".", "-")
    return {"help_content": content, "modal_id": modal_id}
