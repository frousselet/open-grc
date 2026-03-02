from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend


class EmailAuthBackend(BaseBackend):
    """
    Authenticate using email + password.
    Handles lockout check (RA-04) and is_active verification.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        email = kwargs.get("email", username)
        if email is None or password is None:
            return None

        User = get_user_model()
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return None

        if not user.is_active:
            return None

        if user.is_locked:
            return None

        if user.check_password(password):
            return user

        return None

    def get_user(self, user_id):
        User = get_user_model()
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


class PasskeyAuthBackend(BaseBackend):
    """
    Authenticate using a WebAuthn passkey credential ID.
    Called by the passkey login view after WebAuthn verification.
    """

    def authenticate(self, request, passkey_credential_id=None, **kwargs):
        if passkey_credential_id is None:
            return None

        from accounts.models.passkey import Passkey

        try:
            passkey = Passkey.objects.select_related("user").get(
                credential_id=passkey_credential_id,
            )
        except Passkey.DoesNotExist:
            return None

        user = passkey.user
        if not user.is_active:
            return None
        if user.is_locked:
            return None

        return user

    def get_user(self, user_id):
        User = get_user_model()
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


class GroupPermissionBackend(BaseBackend):
    """
    Resolve permissions via custom accounts.Group -> Permission model.
    Permissions follow the dotted codename format: module.feature.action
    """

    def authenticate(self, request, **kwargs):
        return None

    def has_perm(self, user_obj, perm, obj=None):
        if not user_obj.is_active:
            return False
        return perm in self.get_all_permissions(user_obj, obj)

    def has_module_perms(self, user_obj, app_label):
        """Check if user has any permission for the given module."""
        if not user_obj.is_active:
            return False
        prefix = f"{app_label}."
        return any(p.startswith(prefix) for p in self.get_all_permissions(user_obj))

    def get_all_permissions(self, user_obj, obj=None):
        if not user_obj.is_active:
            return set()
        if not hasattr(user_obj, "_custom_perm_cache"):
            from accounts.models import Permission

            perms = Permission.objects.filter(
                groups__users=user_obj
            ).values_list("codename", flat=True)
            user_obj._custom_perm_cache = set(perms)
        return user_obj._custom_perm_cache

    @staticmethod
    def get_allowed_scope_ids(user_obj):
        """Return the set of scope IDs the user may access, or None for unrestricted.

        Rules:
        - Superusers → None (unrestricted)
        - If any group has an empty allowed_scopes → None (unrestricted)
        - Otherwise → union of allowed_scopes across all groups
        """
        if not user_obj.is_active:
            return set()
        if user_obj.is_superuser:
            return None
        if hasattr(user_obj, "_scope_cache"):
            return user_obj._scope_cache

        from accounts.models import Group

        groups = Group.objects.filter(users=user_obj).prefetch_related("allowed_scopes")
        scope_ids = set()
        for group in groups:
            group_scopes = set(group.allowed_scopes.values_list("id", flat=True))
            if not group_scopes:
                # This group has no restriction → user has full access
                user_obj._scope_cache = None
                return None
            scope_ids.update(group_scopes)

        user_obj._scope_cache = scope_ids
        return scope_ids
