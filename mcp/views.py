"""Web views for OAuth credential management on the profile page."""

import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.views import View

from mcp.models import OAuthApplication
from mcp.models.oauth import _generate_client_secret


class OAuthAppCreateView(LoginRequiredMixin, View):
    """Create a new OAuth application (AJAX)."""

    def post(self, request):
        if not request.user.is_superuser and not request.user.has_perm("system.oauth.create"):
            return JsonResponse({"error": "Permission denied."}, status=403)

        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "Invalid JSON."}, status=400)

        name = (body.get("name") or "").strip()
        if not name:
            return JsonResponse({"error": "Name is required."}, status=400)

        raw_secret = _generate_client_secret()
        app = OAuthApplication(name=name, user=request.user)
        app.set_secret(raw_secret)
        app.save()

        return JsonResponse({
            "status": "ok",
            "client_id": app.client_id,
            "client_secret": raw_secret,
        })


class OAuthAppDeleteView(LoginRequiredMixin, View):
    """Delete an OAuth application (AJAX)."""

    def post(self, request, pk):
        if not request.user.is_superuser and not request.user.has_perm("system.oauth.delete"):
            return JsonResponse({"error": "Permission denied."}, status=403)

        try:
            app = OAuthApplication.objects.get(pk=pk, user=request.user)
        except OAuthApplication.DoesNotExist:
            return JsonResponse({"error": "Not found."}, status=404)

        app.delete()
        return JsonResponse({"status": "ok"})


class OAuthAppListView(LoginRequiredMixin, View):
    """Return rendered HTML for the OAuth app list (AJAX partial refresh)."""

    def get(self, request):
        if not request.user.is_superuser and not request.user.has_perm("system.oauth.read"):
            return JsonResponse({"html": ""})

        oauth_apps = request.user.oauth_applications.order_by("-created_at")
        html = render_to_string(
            "mcp/partials/oauth_app_list.html",
            {"oauth_apps": oauth_apps},
            request=request,
        )
        return JsonResponse({"html": html})
