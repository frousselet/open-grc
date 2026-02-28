from itertools import chain
from operator import attrgetter

from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import translation
from django.utils.translation import gettext as _, gettext_lazy as _lazy
from django.views import View
from django.views.generic import DetailView, ListView

from accounts.constants import PERMISSION_REGISTRY, MODULE_LABELS
from accounts.forms import (
    GroupForm,
    LoginForm,
    PasswordChangeForm,
    ProfileForm,
    UserCreateForm,
    UserUpdateForm,
)
from accounts.models import AccessLog, Group, Permission, User
from context.models import Scope


class PermissionRequiredMixin:
    """Mixin checking custom dotted permissions (module.feature.action)."""

    permission_required = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/accounts/login/?next={request.path}")
        if self.permission_required:
            codenames = self.permission_required
            if isinstance(codenames, str):
                codenames = [codenames]
            for codename in codenames:
                if not request.user.has_perm(codename):
                    messages.error(request, _("You do not have the required permissions."))
                    return redirect("/")
        return super().dispatch(request, *args, **kwargs)


# ── Authentication ──────────────────────────────────────────

class LoginView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect("/")
        form = LoginForm()
        return render(request, "accounts/login.html", {"form": form})

    def post(self, request):
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                next_url = request.GET.get("next", "/")
                return redirect(next_url)
            else:
                # Check if account is locked for better messaging
                try:
                    u = User.objects.get(email__iexact=email)
                    if u.is_locked:
                        messages.error(request, _("This account is temporarily locked due to multiple failed attempts."))
                    elif not u.is_active:
                        messages.error(request, _("Invalid credentials."))
                    else:
                        messages.error(request, _("Invalid credentials."))
                except User.DoesNotExist:
                    messages.error(request, _("Invalid credentials."))
        return render(request, "accounts/login.html", {"form": form})


class LogoutView(LoginRequiredMixin, View):
    def post(self, request):
        logout(request)
        return redirect("accounts:login")

    def get(self, request):
        logout(request)
        return redirect("accounts:login")


# ── Profile ─────────────────────────────────────────────────

class ProfileView(LoginRequiredMixin, View):
    def get(self, request):
        form = ProfileForm(instance=request.user)
        groups = request.user.custom_groups.all()
        permissions = sorted(
            Permission.objects.filter(groups__users=request.user).values_list("codename", flat=True).distinct()
        )
        return render(request, "accounts/profile.html", {
            "form": form,
            "groups": groups,
            "permissions": permissions,
        })

    def post(self, request):
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            lang = form.cleaned_data.get("language", "")
            if lang:
                translation.activate(lang)
            messages.success(request, _("Profile updated."))
            response = redirect("accounts:profile")
            if lang:
                response.set_cookie(settings.LANGUAGE_COOKIE_NAME, lang)
            else:
                response.delete_cookie(settings.LANGUAGE_COOKIE_NAME)
            return response
        groups = request.user.custom_groups.all()
        permissions = sorted(
            Permission.objects.filter(groups__users=request.user).values_list("codename", flat=True).distinct()
        )
        return render(request, "accounts/profile.html", {
            "form": form,
            "groups": groups,
            "permissions": permissions,
        })


class PasswordChangeView(LoginRequiredMixin, View):
    def get(self, request):
        form = PasswordChangeForm(request.user)
        return render(request, "accounts/password_change.html", {"form": form})

    def post(self, request):
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, _("Password changed successfully."))
            return redirect("accounts:profile")
        return render(request, "accounts/password_change.html", {"form": form})


# ── Users ───────────────────────────────────────────────────

class UserListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = User
    template_name = "accounts/user_list.html"
    context_object_name = "users"
    paginate_by = 25
    permission_required = "system.users.read"

    def get_queryset(self):
        qs = User.objects.annotate(group_count=Count("custom_groups"))
        q = self.request.GET.get("q")
        status = self.request.GET.get("status")
        if q:
            qs = qs.filter(
                Q(email__icontains=q)
                | Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
            )
        if status == "active":
            qs = qs.filter(is_active=True)
        elif status == "inactive":
            qs = qs.filter(is_active=False)
        return qs


class UserDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = User
    template_name = "accounts/user_detail.html"
    context_object_name = "account_user"
    permission_required = "system.users.read"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        u = self.object
        ctx["groups"] = u.custom_groups.all()
        ctx["permissions"] = sorted(
            Permission.objects.filter(groups__users=u).values_list("codename", flat=True).distinct()
        )
        ctx["recent_access_logs"] = AccessLog.objects.filter(user=u)[:20]
        return ctx


class UserCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "system.users.create"

    def get(self, request):
        form = UserCreateForm()
        return render(request, "accounts/user_form.html", {"form": form, "title": _("Create a user")})

    def post(self, request):
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.created_by = request.user
            user.save()
            messages.success(request, _("User %(name)s created.") % {"name": user.display_name})
            return redirect("accounts:user-detail", pk=user.pk)
        return render(request, "accounts/user_form.html", {"form": form, "title": _("Create a user")})


class UserUpdateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "system.users.update"

    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        form = UserUpdateForm(instance=user)
        return render(request, "accounts/user_form.html", {"form": form, "title": _("Edit %(name)s") % {"name": user.display_name}, "object": user})

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        form = UserUpdateForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, _("User updated."))
            return redirect("accounts:user-detail", pk=user.pk)
        return render(request, "accounts/user_form.html", {"form": form, "title": _("Edit %(name)s") % {"name": user.display_name}, "object": user})


# ── Groups ──────────────────────────────────────────────────

class GroupListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Group
    template_name = "accounts/group_list.html"
    context_object_name = "groups"
    paginate_by = 25
    permission_required = "system.groups.read"

    def get_queryset(self):
        return Group.objects.annotate(
            user_count=Count("users"),
            permission_count=Count("permissions"),
        )


class GroupDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Group
    template_name = "accounts/group_detail.html"
    context_object_name = "group"
    permission_required = "system.groups.read"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        group = self.object
        ctx["group_users"] = group.users.all()
        ctx["group_permissions"] = group.permissions.all().order_by("module", "feature", "action")

        # Build permission matrix as a flat list of rows for easy template rendering
        group_codenames = set(group.permissions.values_list("codename", flat=True))
        all_actions = ["create", "read", "update", "delete", "access", "approve"]
        matrix = []
        for module, features in PERMISSION_REGISTRY.items():
            module_label = MODULE_LABELS.get(module, module)
            for feature, info in features.items():
                cells = []
                for action in all_actions:
                    codename = f"{module}.{feature}.{action}"
                    has_action = action in info["actions"]
                    cells.append({
                        "codename": codename,
                        "has_action": has_action,
                        "checked": codename in group_codenames,
                    })
                matrix.append({
                    "module": module,
                    "module_label": module_label,
                    "feature": feature,
                    "feature_label": info["label"],
                    "cells": cells,
                })
        ctx["permission_matrix"] = matrix
        ctx["all_actions"] = all_actions
        ctx["all_users"] = User.objects.filter(is_active=True).exclude(pk__in=group.users.all())
        ctx["all_scopes"] = Scope.objects.exclude(status="archived")
        ctx["group_scope_ids"] = set(group.allowed_scopes.values_list("id", flat=True))
        return ctx


class GroupCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "system.groups.create"

    def get(self, request):
        form = GroupForm()
        return render(request, "accounts/group_form.html", {"form": form, "title": _("Create a group")})

    def post(self, request):
        form = GroupForm(request.POST)
        if form.is_valid():
            group = form.save(commit=False)
            group.created_by = request.user
            group.save()
            messages.success(request, _("Group '%(name)s' created.") % {"name": group.name})
            return redirect("accounts:group-detail", pk=group.pk)
        return render(request, "accounts/group_form.html", {"form": form, "title": _("Create a group")})


class GroupUpdateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "system.groups.update"

    def get(self, request, pk):
        group = get_object_or_404(Group, pk=pk)
        if group.is_system:
            messages.error(request, _("System groups cannot be modified."))
            return redirect("accounts:group-detail", pk=group.pk)
        form = GroupForm(instance=group)
        return render(request, "accounts/group_form.html", {"form": form, "title": _("Edit '%(name)s'") % {"name": group.name}, "object": group})

    def post(self, request, pk):
        group = get_object_or_404(Group, pk=pk)
        if group.is_system:
            messages.error(request, _("System groups cannot be modified."))
            return redirect("accounts:group-detail", pk=group.pk)
        form = GroupForm(request.POST, instance=group)
        if form.is_valid():
            form.save()
            messages.success(request, _("Group updated."))
            return redirect("accounts:group-detail", pk=group.pk)
        return render(request, "accounts/group_form.html", {"form": form, "title": _("Edit '%(name)s'") % {"name": group.name}, "object": group})


class GroupPermissionsUpdateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Handle permission matrix checkbox form submission."""

    permission_required = "system.groups.update"

    def post(self, request, pk):
        group = get_object_or_404(Group, pk=pk)
        if group.is_system:
            messages.error(request, _("System groups cannot be modified."))
            return redirect("accounts:group-detail", pk=group.pk)

        # Collect selected permission codenames from POST
        selected = request.POST.getlist("permissions")
        perms = Permission.objects.filter(codename__in=selected)
        group.permissions.set(perms)
        messages.success(request, _("Permissions updated."))
        return redirect("accounts:group-detail", pk=group.pk)


class GroupUsersUpdateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Add/remove users from a group."""

    permission_required = "system.groups.update"

    def post(self, request, pk):
        group = get_object_or_404(Group, pk=pk)
        action = request.POST.get("action")
        user_id = request.POST.get("user_id")

        if action == "add" and user_id:
            user = get_object_or_404(User, pk=user_id)
            group.users.add(user)
            messages.success(request, _("%(name)s added to the group.") % {"name": user.display_name})
        elif action == "remove" and user_id:
            user = get_object_or_404(User, pk=user_id)
            group.users.remove(user)
            messages.success(request, _("%(name)s removed from the group.") % {"name": user.display_name})

        return redirect("accounts:group-detail", pk=group.pk)


class GroupScopesUpdateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Update allowed scopes for a group."""

    permission_required = "system.groups.update"

    def post(self, request, pk):
        group = get_object_or_404(Group, pk=pk)
        selected = request.POST.getlist("scopes")
        scopes = Scope.objects.filter(id__in=selected)
        group.allowed_scopes.set(scopes)
        messages.success(request, _("Allowed scopes updated."))
        return redirect("accounts:group-detail", pk=group.pk)


# ── Permissions ─────────────────────────────────────────────

class PermissionListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Permission
    template_name = "accounts/permission_list.html"
    context_object_name = "permissions"
    paginate_by = 100
    permission_required = "system.groups.read"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Group permissions by module -> feature
        grouped = {}
        for perm in Permission.objects.all():
            if perm.module not in grouped:
                grouped[perm.module] = {"label": MODULE_LABELS.get(perm.module, perm.module), "features": {}}
            if perm.feature not in grouped[perm.module]["features"]:
                feature_info = PERMISSION_REGISTRY.get(perm.module, {}).get(perm.feature, {})
                grouped[perm.module]["features"][perm.feature] = {
                    "label": feature_info.get("label", perm.feature),
                    "permissions": [],
                }
            grouped[perm.module]["features"][perm.feature]["permissions"].append(perm)
        ctx["grouped_permissions"] = grouped
        return ctx


# ── Access Logs ─────────────────────────────────────────────

class AccessLogListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = AccessLog
    template_name = "accounts/access_log_list.html"
    context_object_name = "logs"
    paginate_by = 50
    permission_required = "system.audit_trail.read"

    def get_queryset(self):
        qs = AccessLog.objects.select_related("user")
        event_type = self.request.GET.get("event_type")
        email = self.request.GET.get("email")
        date_from = self.request.GET.get("date_from")
        date_to = self.request.GET.get("date_to")
        if event_type:
            qs = qs.filter(event_type=event_type)
        if email:
            qs = qs.filter(email_attempted__icontains=email)
        if date_from:
            qs = qs.filter(timestamp__date__gte=date_from)
        if date_to:
            qs = qs.filter(timestamp__date__lte=date_to)
        return qs


# ── Action Log (history) ────────────────────────────────────

HISTORY_TYPE_LABELS = {"+": _lazy("Creation"), "~": _lazy("Modification"), "-": _lazy("Deletion")}
APPROVAL_FIELDS = {"is_approved", "approved_by", "approved_by_id", "approved_at"}

MODEL_LABELS = {}


def _get_model_labels():
    """Build a mapping of historical model → human label, cached."""
    if MODEL_LABELS:
        return MODEL_LABELS
    for model in apps.get_models():
        if model.__name__.startswith("Historical"):
            original = getattr(model, "instance_type", None)
            if original:
                label = original._meta.verbose_name.capitalize()
                app = original._meta.app_label
                MODEL_LABELS[model] = (app, label)
    return MODEL_LABELS


def _detect_approval(record):
    """Detect if a history record is an approval-only change.

    Returns "approved", "rejected", or None.
    """
    if record.history_type != "~":
        return None
    try:
        prev = record.prev_record
    except Exception:
        return None
    if prev is None:
        return None
    try:
        delta = record.diff_against(prev)
    except Exception:
        return None
    changed_fields = {c.field for c in delta.changes}
    non_approval = changed_fields - APPROVAL_FIELDS - {"version"}
    if non_approval:
        return None
    approval_changed = changed_fields & APPROVAL_FIELDS
    if not approval_changed:
        return None
    return "approved" if getattr(record, "is_approved", False) else "rejected"


class ActionLogListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    template_name = "accounts/action_log_list.html"
    context_object_name = "entries"
    paginate_by = 50
    permission_required = "system.audit_trail.read"

    def _get_historical_models(self):
        return [m for m in apps.get_models() if m.__name__.startswith("Historical")]

    def get_queryset(self):
        labels = _get_model_labels()
        module = self.request.GET.get("module")
        user_filter = self.request.GET.get("user")
        action = self.request.GET.get("action")
        date_from = self.request.GET.get("date_from")
        date_to = self.request.GET.get("date_to")

        # For the approval filter we need post-processing; for others we can filter at DB level
        filter_approval = action == "approval"

        querysets = []
        for hist_model in self._get_historical_models():
            app, model_label = labels.get(hist_model, (None, None))
            if not app:
                continue
            if module and app != module:
                continue
            # Check model has approval fields, skip if filtering approvals on non-approvable
            has_approval = hasattr(hist_model, "is_approved")
            if filter_approval and not has_approval:
                continue
            qs = hist_model.objects.all()
            if user_filter:
                qs = qs.filter(history_user_id=user_filter)
            if action and not filter_approval:
                qs = qs.filter(history_type=action)
            if filter_approval:
                # Pre-filter to modifications only
                qs = qs.filter(history_type="~")
            if date_from:
                qs = qs.filter(history_date__date__gte=date_from)
            if date_to:
                qs = qs.filter(history_date__date__lte=date_to)
            querysets.append(qs)

        if not querysets:
            return []

        merged = sorted(
            chain(*querysets),
            key=attrgetter("history_date"),
            reverse=True,
        )
        return merged

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        labels = _get_model_labels()
        filter_approval = self.request.GET.get("action") == "approval"

        annotated = []
        for entry in ctx["entries"]:
            app, model_label = labels.get(type(entry), ("", ""))
            entry.app_label = MODULE_LABELS.get(app, app)
            entry.model_label = model_label
            entry.object_repr = str(entry)

            # Detect approval
            approval_status = _detect_approval(entry)
            if approval_status == "approved":
                entry.action_label = _("Approval")
                entry.action_badge = "info"
            elif approval_status == "rejected":
                entry.action_label = _("Approval withdrawn")
                entry.action_badge = "dark"
            else:
                entry.action_label = HISTORY_TYPE_LABELS.get(entry.history_type, "?")
                if entry.history_type == "+":
                    entry.action_badge = "success"
                elif entry.history_type == "~":
                    entry.action_badge = "warning"
                elif entry.history_type == "-":
                    entry.action_badge = "danger"
                else:
                    entry.action_badge = "secondary"
                # If filtering approvals only, skip non-approval entries
                if filter_approval:
                    continue

            annotated.append(entry)

        ctx["entries"] = annotated
        ctx["users"] = User.objects.filter(is_active=True).order_by("first_name", "last_name")
        ctx["module_labels"] = {k: v for k, v in MODULE_LABELS.items() if k != "system"}
        return ctx
