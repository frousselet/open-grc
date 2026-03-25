from django.conf import settings
from django.contrib.auth import login, get_user_model
from django.utils import translation

IMPERSONATION_SESSION_KEY = "_impersonation_original_user_id"


class UserLanguageMiddleware:
    """Activate the authenticated user's language preference.

    Must be placed after AuthenticationMiddleware and after
    LocaleMiddleware so it can override the browser-detected language
    when the user has an explicit preference.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if hasattr(request, "user") and request.user.is_authenticated:
            lang = getattr(request.user, "language", "")
            if lang:
                translation.activate(lang)
                request.LANGUAGE_CODE = lang

        response = self.get_response(request)

        if hasattr(request, "user") and request.user.is_authenticated:
            lang = getattr(request.user, "language", "")
            if lang:
                response.set_cookie(settings.LANGUAGE_COOKIE_NAME, lang)
            else:
                # Auto mode: delete any stale cookie so LocaleMiddleware
                # falls back to Accept-Language header.
                response.delete_cookie(settings.LANGUAGE_COOKIE_NAME)

        return response


class ImpersonationMiddleware:
    """Expose impersonation state on every request.

    Sets ``request.impersonator`` to the original admin User if
    impersonation is active, or ``None`` otherwise. If the original
    admin no longer has permission or is inactive, impersonation is
    terminated automatically.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.impersonator = None

        if not hasattr(request, "user") or not request.user.is_authenticated:
            return self.get_response(request)

        original_id = request.session.get(IMPERSONATION_SESSION_KEY)
        if not original_id:
            return self.get_response(request)

        User = get_user_model()
        try:
            original_user = User.objects.get(pk=original_id)
        except User.DoesNotExist:
            # Original admin deleted, stop impersonation
            del request.session[IMPERSONATION_SESSION_KEY]
            return self.get_response(request)

        if not original_user.is_active or not original_user.has_perm("system.users.impersonate"):
            # Permission revoked or account deactivated, restore
            login(request, original_user, backend="accounts.backends.EmailAuthBackend")
            request.session.pop(IMPERSONATION_SESSION_KEY, None)
            return self.get_response(request)

        request.impersonator = original_user
        return self.get_response(request)
