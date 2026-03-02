import json
import logging

from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_protect

from accounts.constants import AccessEventType
from accounts.models import AccessLog, Passkey

logger = logging.getLogger(__name__)

_fido2_initialized = False


def _ensure_fido2():
    """Lazy-initialize fido2 feature flags on first use."""
    global _fido2_initialized
    if not _fido2_initialized:
        import fido2.features
        fido2.features.webauthn_json_mapping.enabled = True
        _fido2_initialized = True


def _get_server(request):
    """Build a Fido2Server using explicit settings or request-derived values."""
    _ensure_fido2()
    from fido2.server import Fido2Server
    from fido2.webauthn import PublicKeyCredentialRpEntity

    rp_id = settings.WEBAUTHN_RP_ID
    origin = settings.WEBAUTHN_ORIGIN

    if rp_id is None or origin is None:
        host = request.get_host().split(":")[0]
        scheme = "https" if request.is_secure() else "http"
        derived_origin = f"{scheme}://{request.get_host()}"
        if rp_id is None:
            rp_id = host
        if origin is None:
            origin = derived_origin

    expected_origin = origin
    rp = PublicKeyCredentialRpEntity(id=rp_id, name=settings.WEBAUTHN_RP_NAME)
    return Fido2Server(
        rp,
        verify_origin=lambda o: o == expected_origin,
    )


def _get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


# ── Registration (authenticated user — profile page) ──────


@method_decorator(csrf_protect, name="dispatch")
class PasskeyRegisterBeginView(LoginRequiredMixin, View):
    """Start passkey registration: return WebAuthn creation options."""

    def post(self, request):
        from fido2.webauthn import (
            PublicKeyCredentialUserEntity,
            ResidentKeyRequirement,
            UserVerificationRequirement,
        )

        server = _get_server(request)
        user = request.user

        # Build exclude list from existing passkeys
        existing = Passkey.objects.filter(user=user)
        exclude_credentials = [
            {"type": "public-key", "id": bytes(pk.credential_id)}
            for pk in existing
        ]

        user_entity = PublicKeyCredentialUserEntity(
            id=str(user.id).encode(),
            name=user.email,
            display_name=user.display_name,
        )

        options, state = server.register_begin(
            user=user_entity,
            credentials=exclude_credentials or None,
            resident_key_requirement=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        )

        request.session["webauthn_register_state"] = state
        return JsonResponse(dict(options))


@method_decorator(csrf_protect, name="dispatch")
class PasskeyRegisterCompleteView(LoginRequiredMixin, View):
    """Complete passkey registration: verify and store the credential."""

    def post(self, request):
        from fido2 import cbor

        server = _get_server(request)
        state = request.session.pop("webauthn_register_state", None)
        if state is None:
            return JsonResponse({"error": "No registration in progress."}, status=400)

        try:
            data = json.loads(request.body)
            name = data.get("name", "").strip() or "Passkey"
            response = data.get("credential")
            auth_data = server.register_complete(state, response)
        except Exception:
            logger.exception("Passkey registration failed")
            return JsonResponse({"error": "Registration failed."}, status=400)

        cred = auth_data.credential_data
        Passkey.objects.create(
            user=request.user,
            name=name,
            credential_id=cred.credential_id,
            public_key=cbor.encode(dict(cred.public_key)),
            sign_count=auth_data.counter,
        )

        AccessLog.objects.create(
            user=request.user,
            email_attempted=request.user.email,
            event_type=AccessEventType.PASSKEY_REGISTERED,
            ip_address=_get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            metadata={"passkey_name": name},
        )

        return JsonResponse({"status": "ok"})


# ── Authentication (unauthenticated — login page) ─────────


@method_decorator(csrf_protect, name="dispatch")
class PasskeyLoginBeginView(View):
    """Start passkey authentication: return WebAuthn request options."""

    def post(self, request):
        from fido2.webauthn import UserVerificationRequirement

        server = _get_server(request)

        # Discoverable credentials: no allow_credentials list
        options, state = server.authenticate_begin(
            user_verification=UserVerificationRequirement.PREFERRED,
        )

        request.session["webauthn_auth_state"] = state
        return JsonResponse(dict(options))


@method_decorator(csrf_protect, name="dispatch")
class PasskeyLoginCompleteView(View):
    """Complete passkey authentication: verify assertion and log in."""

    def post(self, request):
        from fido2 import cbor
        from fido2.cose import CoseKey
        from fido2.webauthn import AttestedCredentialData

        server = _get_server(request)
        state = request.session.pop("webauthn_auth_state", None)
        if state is None:
            return JsonResponse({"error": "No authentication in progress."}, status=400)

        try:
            data = json.loads(request.body)
            response = data.get("credential")

            # Build credentials list from all stored passkeys
            all_passkeys = Passkey.objects.select_related("user").all()
            credentials = []
            passkey_map = {}
            for pk in all_passkeys:
                public_key = CoseKey.parse(cbor.decode(bytes(pk.public_key)))
                cred_data = AttestedCredentialData.create(
                    b"\x00" * 16,  # aaguid placeholder
                    bytes(pk.credential_id),
                    public_key,
                )
                credentials.append(cred_data)
                passkey_map[bytes(pk.credential_id)] = pk

            cred = server.authenticate_complete(state, credentials, response)
        except Exception:
            logger.exception("Passkey authentication failed")
            AccessLog.objects.create(
                email_attempted="",
                event_type=AccessEventType.PASSKEY_LOGIN_FAILED,
                ip_address=_get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )
            return JsonResponse({"error": "Authentication failed."}, status=400)

        passkey = passkey_map.get(cred.credential_id)
        if passkey is None:
            return JsonResponse({"error": "Unknown credential."}, status=400)

        user = authenticate(request, passkey_credential_id=bytes(passkey.credential_id))
        if user is None:
            return JsonResponse({"error": "Account unavailable."}, status=403)

        login(request, user, backend="accounts.backends.PasskeyAuthBackend")

        # Update passkey usage
        passkey.last_used_at = timezone.now()
        passkey.save(update_fields=["last_used_at"])

        user.reset_failed_attempts()

        AccessLog.objects.create(
            user=user,
            email_attempted=user.email,
            event_type=AccessEventType.PASSKEY_LOGIN_SUCCESS,
            ip_address=_get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        next_url = request.GET.get("next", "/")
        return JsonResponse({"status": "ok", "redirect": next_url})


# ── Management ─────────────────────────────────────────────


@method_decorator(csrf_protect, name="dispatch")
class PasskeyDeleteView(LoginRequiredMixin, View):
    """Delete a passkey owned by the current user."""

    def post(self, request, pk):
        passkey = get_object_or_404(Passkey, pk=pk, user=request.user)
        name = passkey.name

        AccessLog.objects.create(
            user=request.user,
            email_attempted=request.user.email,
            event_type=AccessEventType.PASSKEY_DELETED,
            ip_address=_get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            metadata={"passkey_name": name},
        )

        passkey.delete()
        return JsonResponse({"status": "ok"})


class PasskeyListView(LoginRequiredMixin, View):
    """Return the list of passkeys for the current user (HTML partial)."""

    def get(self, request):
        from django.template.loader import render_to_string

        passkeys = request.user.passkeys.order_by("-created_at")
        html = render_to_string(
            "accounts/partials/passkey_list.html",
            {"passkeys": passkeys},
            request=request,
        )
        return JsonResponse({"html": html})
