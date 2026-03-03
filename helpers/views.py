import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View


class DismissHelperView(LoginRequiredMixin, View):
    """Persist the dismissal of a help banner for the current user."""

    def post(self, request):
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        key = data.get("key", "").strip()
        if not key:
            return JsonResponse({"error": "Missing key"}, status=400)

        dismissed = request.user.dismissed_helpers
        if not isinstance(dismissed, list):
            dismissed = []

        if key not in dismissed:
            dismissed.append(key)
            request.user.dismissed_helpers = dismissed
            request.user.save(update_fields=["dismissed_helpers"])

        return JsonResponse({"status": "ok"})
