from django import template
from django.apps import apps

register = template.Library()


@register.simple_tag
def approval_enabled_for(model_ref):
    """Check if approval is enabled for a model.

    Accepts either a model class or a string like "context.scope".

    Usage in templates:
        {% load versioning_tags %}
        {% approval_enabled_for "context.scope" as show_approval %}
        {% if show_approval %}...{% endif %}
    """
    from core.models import VersioningConfig

    if isinstance(model_ref, str):
        try:
            app_label, model_name = model_ref.split(".")
            model_ref = apps.get_model(app_label, model_name)
        except (ValueError, LookupError):
            return True
    return VersioningConfig.is_approval_enabled(model_ref)
