from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

from accounts.constants import AccessEventType, FailureReason
from accounts.models import AccessLog


def _get_client_ip(request):
    if request is None:
        return None
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _get_user_agent(request):
    if request is None:
        return ""
    return request.META.get("HTTP_USER_AGENT", "")


@receiver(user_logged_in)
def log_login_success(sender, request, user, **kwargs):
    user.reset_failed_attempts()
    AccessLog.objects.create(
        user=user,
        email_attempted=user.email,
        event_type=AccessEventType.LOGIN_SUCCESS,
        ip_address=_get_client_ip(request),
        user_agent=_get_user_agent(request),
    )


@receiver(user_logged_out)
def log_logout(sender, request, user, **kwargs):
    if user and user.is_authenticated:
        AccessLog.objects.create(
            user=user,
            email_attempted=user.email,
            event_type=AccessEventType.LOGOUT,
            ip_address=_get_client_ip(request),
            user_agent=_get_user_agent(request),
        )


@receiver(user_login_failed)
def log_login_failed(sender, credentials, request, **kwargs):
    email = credentials.get("username", credentials.get("email", ""))
    User = get_user_model()

    user = None
    failure_reason = FailureReason.USER_NOT_FOUND

    try:
        user = User.objects.get(email__iexact=email)
        if not user.is_active:
            failure_reason = FailureReason.ACCOUNT_INACTIVE
        elif user.is_locked:
            failure_reason = FailureReason.ACCOUNT_LOCKED
        else:
            failure_reason = FailureReason.INVALID_PASSWORD
            user.increment_failed_attempts()
            # Reload to check if account just got locked
            user.refresh_from_db()
            if user.is_locked:
                AccessLog.objects.create(
                    user=user,
                    email_attempted=email,
                    event_type=AccessEventType.ACCOUNT_LOCKED,
                    ip_address=_get_client_ip(request),
                    user_agent=_get_user_agent(request),
                )
    except User.DoesNotExist:
        pass

    AccessLog.objects.create(
        user=user,
        email_attempted=email,
        event_type=AccessEventType.LOGIN_FAILED,
        ip_address=_get_client_ip(request),
        user_agent=_get_user_agent(request),
        failure_reason=failure_reason,
    )
