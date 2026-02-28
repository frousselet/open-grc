from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def has_perm(context, codename):
    """
    Usage: {% has_perm "system.users.read" as can_view_users %}
    Returns True if the current user has the given permission.
    """
    request = context.get("request")
    if request and hasattr(request, "user") and request.user.is_authenticated:
        return request.user.has_perm(codename)
    return False


@register.simple_tag(takes_context=True)
def has_module_perms(context, module):
    """
    Usage: {% has_module_perms "system" as can_admin %}
    Returns True if the user has any permission for the given module.
    """
    request = context.get("request")
    if request and hasattr(request, "user") and request.user.is_authenticated:
        return request.user.has_module_perms(module)
    return False
