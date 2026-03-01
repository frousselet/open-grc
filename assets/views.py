from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from accounts.mixins import ApprovableUpdateMixin, ApprovalContextMixin, ScopeFilterMixin
from .forms import (
    AssetDependencyForm,
    AssetGroupForm,
    EssentialAssetForm,
    SupplierForm,
    SupplierRequirementForm,
    SupportAssetForm,
)
from .models import (
    AssetDependency,
    AssetGroup,
    EssentialAsset,
    Supplier,
    SupplierRequirement,
    SupportAsset,
)


class CreatedByMixin:
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class HistoryMixin:
    """Add history_records to context for detail views."""

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["history_records"] = self.object.history.select_related("history_user").all()[:50]
        return ctx


class ApproveView(LoginRequiredMixin, View):
    """Generic approve view for assets domain models."""

    model = None
    permission_feature = None
    success_url = None

    def post(self, request, pk):
        obj = get_object_or_404(self.model, pk=pk)
        feature = self.permission_feature or self.model._meta.model_name
        codename = f"assets.{feature}.approve"
        if not request.user.is_superuser and not request.user.has_perm(codename):
            messages.error(request, _("You do not have permission to approve this item."))
            return redirect(request.META.get("HTTP_REFERER", "/"))
        obj.is_approved = True
        obj.approved_by = request.user
        obj.approved_at = timezone.now()
        obj.save(update_fields=["is_approved", "approved_by", "approved_at"])
        messages.success(request, _("Item approved."))
        return redirect(request.META.get("HTTP_REFERER", self.success_url or "/"))


# ── Dashboard ───────────────────────────────────────────────

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "assets/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.now().date()
        ctx["essential_count"] = EssentialAsset.objects.count()
        ctx["support_count"] = SupportAsset.objects.count()
        ctx["dependency_count"] = AssetDependency.objects.count()
        ctx["group_count"] = AssetGroup.objects.count()
        ctx["essential_by_type"] = (
            EssentialAsset.objects.values("type")
            .annotate(count=Count("id"))
            .order_by("type")
        )
        ctx["support_by_type"] = (
            SupportAsset.objects.values("type")
            .annotate(count=Count("id"))
            .order_by("type")
        )
        ctx["unsupported_essentials"] = EssentialAsset.objects.filter(
            dependencies_as_essential__isnull=True
        ).count()
        ctx["orphan_supports"] = SupportAsset.objects.filter(
            dependencies_as_support__isnull=True
        ).count()
        ctx["spof_count"] = AssetDependency.objects.filter(
            is_single_point_of_failure=True,
        ).count()
        ctx["eol_assets"] = SupportAsset.objects.filter(
            end_of_life_date__lte=today,
            status="active",
        )[:10]
        ctx["personal_data_count"] = EssentialAsset.objects.filter(
            personal_data=True
        ).count()
        return ctx


# ── Essential Asset ─────────────────────────────────────────

class EssentialAssetListView(LoginRequiredMixin, ScopeFilterMixin, ListView):
    model = EssentialAsset
    template_name = "assets/essential_asset_list.html"
    context_object_name = "assets"
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related("scope", "owner")
        asset_type = self.request.GET.get("type")
        if asset_type:
            qs = qs.filter(type=asset_type)
        status_filter = self.request.GET.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


class EssentialAssetDetailView(LoginRequiredMixin, ScopeFilterMixin, ApprovalContextMixin, HistoryMixin, DetailView):
    model = EssentialAsset
    template_name = "assets/essential_asset_detail.html"
    context_object_name = "asset"
    approval_feature = "essential_asset"
    approve_url_name = "assets:essential-asset-approve"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["dependencies"] = self.object.dependencies_as_essential.select_related(
            "support_asset"
        )
        ctx["valuations"] = self.object.valuations.all()[:10]
        return ctx


class EssentialAssetCreateView(LoginRequiredMixin, CreatedByMixin, CreateView):
    model = EssentialAsset
    form_class = EssentialAssetForm
    template_name = "assets/essential_asset_form.html"
    success_url = reverse_lazy("assets:essential-asset-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class EssentialAssetUpdateView(LoginRequiredMixin, ApprovableUpdateMixin, ScopeFilterMixin, UpdateView):
    model = EssentialAsset
    form_class = EssentialAssetForm
    template_name = "assets/essential_asset_form.html"
    success_url = reverse_lazy("assets:essential-asset-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class EssentialAssetDeleteView(LoginRequiredMixin, DeleteView):
    model = EssentialAsset
    template_name = "assets/confirm_delete.html"
    success_url = reverse_lazy("assets:essential-asset-list")


# ── Support Asset ───────────────────────────────────────────

class SupportAssetListView(LoginRequiredMixin, ScopeFilterMixin, ListView):
    model = SupportAsset
    template_name = "assets/support_asset_list.html"
    context_object_name = "assets"
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related("scope", "owner")
        asset_type = self.request.GET.get("type")
        if asset_type:
            qs = qs.filter(type=asset_type)
        status_filter = self.request.GET.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


class SupportAssetDetailView(LoginRequiredMixin, ScopeFilterMixin, ApprovalContextMixin, HistoryMixin, DetailView):
    model = SupportAsset
    template_name = "assets/support_asset_detail.html"
    context_object_name = "asset"
    approval_feature = "support_asset"
    approve_url_name = "assets:support-asset-approve"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["dependencies"] = self.object.dependencies_as_support.select_related(
            "essential_asset"
        )
        ctx["children"] = self.object.children.all()
        return ctx


class SupportAssetCreateView(LoginRequiredMixin, CreatedByMixin, CreateView):
    model = SupportAsset
    form_class = SupportAssetForm
    template_name = "assets/support_asset_form.html"
    success_url = reverse_lazy("assets:support-asset-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class SupportAssetUpdateView(LoginRequiredMixin, ApprovableUpdateMixin, ScopeFilterMixin, UpdateView):
    model = SupportAsset
    form_class = SupportAssetForm
    template_name = "assets/support_asset_form.html"
    success_url = reverse_lazy("assets:support-asset-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class SupportAssetDeleteView(LoginRequiredMixin, DeleteView):
    model = SupportAsset
    template_name = "assets/confirm_delete.html"
    success_url = reverse_lazy("assets:support-asset-list")


# ── Dependency ──────────────────────────────────────────────

class DependencyListView(LoginRequiredMixin, ListView):
    model = AssetDependency
    template_name = "assets/dependency_list.html"
    context_object_name = "dependencies"
    paginate_by = 25

    def get_queryset(self):
        return super().get_queryset().select_related(
            "essential_asset", "support_asset"
        )


class DependencyCreateView(LoginRequiredMixin, CreatedByMixin, CreateView):
    model = AssetDependency
    form_class = AssetDependencyForm
    template_name = "assets/dependency_form.html"
    success_url = reverse_lazy("assets:dependency-list")


class DependencyUpdateView(LoginRequiredMixin, ApprovableUpdateMixin, UpdateView):
    model = AssetDependency
    form_class = AssetDependencyForm
    template_name = "assets/dependency_form.html"
    success_url = reverse_lazy("assets:dependency-list")


class DependencyDeleteView(LoginRequiredMixin, DeleteView):
    model = AssetDependency
    template_name = "assets/confirm_delete.html"
    success_url = reverse_lazy("assets:dependency-list")


# ── Group ───────────────────────────────────────────────────

class GroupListView(LoginRequiredMixin, ScopeFilterMixin, ListView):
    model = AssetGroup
    template_name = "assets/group_list.html"
    context_object_name = "groups"
    paginate_by = 25

    def get_queryset(self):
        return super().get_queryset().annotate(
            member_count=Count("members")
        )


class GroupDetailView(LoginRequiredMixin, ScopeFilterMixin, ApprovalContextMixin, HistoryMixin, DetailView):
    model = AssetGroup
    template_name = "assets/group_detail.html"
    context_object_name = "group"
    approval_feature = "group"
    approve_url_name = "assets:group-approve"

    def get_queryset(self):
        return super().get_queryset().prefetch_related("members")


class GroupCreateView(LoginRequiredMixin, CreatedByMixin, CreateView):
    model = AssetGroup
    form_class = AssetGroupForm
    template_name = "assets/group_form.html"
    success_url = reverse_lazy("assets:group-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class GroupUpdateView(LoginRequiredMixin, ApprovableUpdateMixin, ScopeFilterMixin, UpdateView):
    model = AssetGroup
    form_class = AssetGroupForm
    template_name = "assets/group_form.html"
    success_url = reverse_lazy("assets:group-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class GroupDeleteView(LoginRequiredMixin, DeleteView):
    model = AssetGroup
    template_name = "assets/confirm_delete.html"
    success_url = reverse_lazy("assets:group-list")


# ── Supplier ──────────────────────────────────────────────

class SupplierListView(LoginRequiredMixin, ScopeFilterMixin, ListView):
    model = Supplier
    template_name = "assets/supplier_list.html"
    context_object_name = "suppliers"
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related("scope", "owner")
        supplier_type = self.request.GET.get("type")
        if supplier_type:
            qs = qs.filter(type=supplier_type)
        status_filter = self.request.GET.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


class SupplierDetailView(LoginRequiredMixin, ScopeFilterMixin, ApprovalContextMixin, HistoryMixin, DetailView):
    model = Supplier
    template_name = "assets/supplier_detail.html"
    context_object_name = "supplier"
    approval_feature = "supplier"
    approve_url_name = "assets:supplier-approve"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["requirements"] = self.object.requirements.select_related(
            "requirement", "verified_by"
        )
        ctx["compliance_summary"] = self.object.requirement_compliance_summary
        return ctx


class SupplierCreateView(LoginRequiredMixin, CreatedByMixin, CreateView):
    model = Supplier
    form_class = SupplierForm
    template_name = "assets/supplier_form.html"
    success_url = reverse_lazy("assets:supplier-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class SupplierUpdateView(LoginRequiredMixin, ApprovableUpdateMixin, ScopeFilterMixin, UpdateView):
    model = Supplier
    form_class = SupplierForm
    template_name = "assets/supplier_form.html"
    success_url = reverse_lazy("assets:supplier-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class SupplierDeleteView(LoginRequiredMixin, DeleteView):
    model = Supplier
    template_name = "assets/confirm_delete.html"
    success_url = reverse_lazy("assets:supplier-list")


class SupplierArchiveView(LoginRequiredMixin, View):
    """Archive a supplier (set status to 'archived')."""

    def post(self, request, pk):
        supplier = get_object_or_404(Supplier, pk=pk)
        supplier.status = "archived"
        supplier.save(update_fields=["status"])
        messages.success(request, _("Supplier archived."))
        return redirect("assets:supplier-list")


# ── Supplier Requirements ─────────────────────────────────

class SupplierRequirementCreateView(LoginRequiredMixin, CreateView):
    model = SupplierRequirement
    form_class = SupplierRequirementForm
    template_name = "assets/supplier_requirement_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.supplier = get_object_or_404(Supplier, pk=kwargs["supplier_pk"])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.supplier = self.supplier
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["supplier"] = self.supplier
        return ctx

    def get_success_url(self):
        return reverse_lazy("assets:supplier-detail", kwargs={"pk": self.supplier.pk})


class SupplierRequirementUpdateView(LoginRequiredMixin, UpdateView):
    model = SupplierRequirement
    form_class = SupplierRequirementForm
    template_name = "assets/supplier_requirement_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["supplier"] = self.object.supplier
        return ctx

    def get_success_url(self):
        return reverse_lazy("assets:supplier-detail", kwargs={"pk": self.object.supplier.pk})


class SupplierRequirementDeleteView(LoginRequiredMixin, DeleteView):
    model = SupplierRequirement
    template_name = "assets/confirm_delete.html"

    def get_success_url(self):
        return reverse_lazy("assets:supplier-detail", kwargs={"pk": self.object.supplier.pk})
