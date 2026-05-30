from django import template

register = template.Library()


@register.filter
def initials(name):
    """Return up to two uppercase initials extracted from a display name.

    Examples::

        "François Rousselet" -> "FR"
        "François"           -> "F"
        "alice"              -> "A"
        ""                   -> "?"

    Replaces the buggy ``{{ name|truncatechars:1 }}`` pattern, which always
    rendered ``...`` because Django's truncatechars counts the marker in
    the length budget.
    """
    parts = [p for p in (name or "").split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][0].upper()
    return (parts[0][0] + parts[-1][0]).upper()


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


@register.inclusion_tag("includes/user_badge.html")
def user_badge(user, size=28, link=False, name=True, block=False):
    """Render a user avatar + display name badge.

    Usage:
        {% load accounts_tags %}
        {% user_badge some_user %}
        {% user_badge some_user size=32 link=True %}
        {% user_badge some_user size=24 name=False %}

    Parameters:
        user  - User instance (required)
        size  - Avatar diameter in px (default 28)
        link  - Render name as link to user detail (default False)
        name  - Show display name next to avatar (default True)
        block - Use d-flex instead of d-inline-flex (default False)
    """
    size = int(size)
    if size >= 48:
        font_size = "1.125rem"
    elif size >= 32:
        font_size = ".75rem"
    else:
        font_size = ".625rem"

    avatar_src = ""
    if user and user.avatar:
        if size > 32:
            avatar_src = user.avatar_64 or user.avatar
        elif size > 16:
            avatar_src = user.avatar_32 or user.avatar
        else:
            avatar_src = user.avatar_16 or user.avatar

    initial = initials(user.display_name if user else "")

    return {
        "u": user,
        "sz": size,
        "avatar_src": avatar_src,
        "font_size": font_size,
        "initial": initial,
        "show_name": name,
        "link": link,
        "block": block,
    }
