from django.conf import settings
from django.utils import translation


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
