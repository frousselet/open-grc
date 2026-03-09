from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from accounts.views import PermissionRequiredMixin

from .forms import VersioningConfigForm, get_model_field_choices
from .models import VersioningConfig


class VersioningConfigListView(
    LoginRequiredMixin, PermissionRequiredMixin, ListView,
):
    model = VersioningConfig
    template_name = "core/versioning_config_list.html"
    context_object_name = "configs"
    permission_required = "system.config.read"
    paginate_by = 50


class VersioningConfigCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, CreateView,
):
    model = VersioningConfig
    form_class = VersioningConfigForm
    template_name = "core/versioning_config_form.html"
    permission_required = "system.config.update"
    success_url = reverse_lazy("core:versioning-config-list")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Versioning configuration created."))
        return response


class VersioningConfigUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, UpdateView,
):
    model = VersioningConfig
    form_class = VersioningConfigForm
    template_name = "core/versioning_config_form.html"
    permission_required = "system.config.update"
    success_url = reverse_lazy("core:versioning-config-list")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Versioning configuration updated."))
        return response


class VersioningConfigDeleteView(
    LoginRequiredMixin, PermissionRequiredMixin, DeleteView,
):
    model = VersioningConfig
    template_name = "core/versioning_config_confirm_delete.html"
    permission_required = "system.config.update"
    success_url = reverse_lazy("core:versioning-config-list")

    def form_valid(self, form):
        messages.success(self.request, _("Versioning configuration deleted."))
        return super().form_valid(form)


class VersioningFieldChoicesView(LoginRequiredMixin, View):
    """AJAX endpoint: return the field choices for a given model_name."""

    def get(self, request):
        model_name = request.GET.get("model_name", "")
        choices = get_model_field_choices(model_name)
        return JsonResponse(
            [{"value": c[0], "label": c[1]} for c in choices],
            safe=False,
        )
