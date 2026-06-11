from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from accounts.mixins import ApprovableUpdateMixin, ApprovalContextMixin, ScopeFilterMixin, WorkflowStepperMixin
from accounts.views import PermissionRequiredMixin
from core.mixins import HtmxFormMixin, SortableListMixin
from context.models import Scope, Site
from .forms import (
    AssetDependencyForm,
    AssetGroupCreateForm,
    AssetGroupUpdateForm,
    EssentialAssetCreateForm,
    EssentialAssetUpdateForm,
    SiteAssetDependencyForm,
    SiteCreateForm,
    SiteUpdateForm,
    SiteSupplierDependencyForm,
    SupplierDependencyForm,
    SupplierCreateForm,
    SupplierUpdateForm,
    SupplierRequirementForm,
    SupplierRequirementReviewForm,
    SupplierTypeForm,
    SupplierTypeRequirementForm,
    SupplierTypeRequirementFormSet,
    SupportAssetCreateForm,
    SupportAssetUpdateForm,
)
from .models import (
    AssetDependency,
    AssetGroup,
    EssentialAsset,
    SiteAssetDependency,
    SiteSupplierDependency,
    Supplier,
    SupplierDependency,
    SupplierRequirement,
    SupplierRequirementReview,
    SupplierType,
    SupplierTypeRequirement,
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
        from core.models import VersioningConfig

        obj = get_object_or_404(self.model, pk=pk)
        if not VersioningConfig.is_approval_enabled(self.model):
            messages.error(request, _("Approval is disabled for this item type."))
            return redirect(request.META.get("HTTP_REFERER", "/"))
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


# ── Essential Asset ─────────────────────────────────────────

class EssentialAssetListView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = EssentialAsset
    template_name = "assets/essential_asset_list.html"
    context_object_name = "assets"
    permission_required = "assets.essential_asset.read"
    paginate_by = 25
    sortable_fields = {
        "reference": "reference",
        "name": "name",
        "type": "type",
        "category": "category",
        "owner": "owner__last_name",
        "workflow_state": "workflow_state",
    }
    default_sort = "reference"
    search_fields = ["reference", "name", "owner__last_name", "owner__first_name"]

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related("scopes").select_related("owner")
        asset_type = self.request.GET.get("type")
        if asset_type:
            qs = qs.filter(type=asset_type)
        status_filter = self.request.GET.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


class EssentialAssetDetailView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, ApprovalContextMixin, HistoryMixin, WorkflowStepperMixin, DetailView):
    model = EssentialAsset
    template_name = "assets/essential_asset_detail.html"
    context_object_name = "asset"
    permission_required = "assets.essential_asset.read"
    approval_feature = "essential_asset"
    approve_url_name = "assets:essential-asset-approve"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["dependencies"] = self.object.dependencies_as_essential.select_related(
            "support_asset"
        )
        ctx["valuations"] = self.object.valuations.all()[:10]
        return ctx


class EssentialAssetCreateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, CreatedByMixin, CreateView):
    model = EssentialAsset
    form_class = EssentialAssetCreateForm
    template_name = "assets/essential_asset_form.html"
    permission_required = "assets.essential_asset.create"
    modal_template_name = "assets/essential_asset_form_modal.html"
    modal_title_create = _l("New essential asset")
    modal_title_update = _l("Edit essential asset")
    success_url = reverse_lazy("assets:essential-asset-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class EssentialAssetUpdateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, ApprovableUpdateMixin, ScopeFilterMixin, UpdateView):
    model = EssentialAsset
    form_class = EssentialAssetUpdateForm
    template_name = "assets/essential_asset_form.html"
    permission_required = "assets.essential_asset.update"
    modal_template_name = "assets/essential_asset_form_modal.html"
    modal_title_create = _l("New essential asset")
    modal_title_update = _l("Edit essential asset")
    success_url = reverse_lazy("assets:essential-asset-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class EssentialAssetDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = EssentialAsset
    template_name = "assets/confirm_delete.html"
    permission_required = "assets.essential_asset.delete"
    success_url = reverse_lazy("assets:essential-asset-list")


# ── Support Asset ───────────────────────────────────────────

class SupportAssetListView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = SupportAsset
    template_name = "assets/support_asset_list.html"
    context_object_name = "assets"
    permission_required = "assets.support_asset.read"
    paginate_by = 25
    sortable_fields = {
        "reference": "reference",
        "name": "name",
        "type": "type",
        "category": "category",
        "owner": "owner__last_name",
        "workflow_state": "workflow_state",
        "eol": "end_of_life_date",
    }
    default_sort = "reference"
    search_fields = ["reference", "name", "owner__last_name", "owner__first_name"]

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related("scopes").select_related("owner")
        asset_type = self.request.GET.get("type")
        if asset_type:
            qs = qs.filter(type=asset_type)
        status_filter = self.request.GET.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


class SupportAssetDetailView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, ApprovalContextMixin, HistoryMixin, WorkflowStepperMixin, DetailView):
    model = SupportAsset
    template_name = "assets/support_asset_detail.html"
    context_object_name = "asset"
    permission_required = "assets.support_asset.read"
    approval_feature = "support_asset"
    approve_url_name = "assets:support-asset-approve"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["dependencies"] = self.object.dependencies_as_support.select_related(
            "essential_asset"
        )
        ctx["children"] = self.object.children.all()
        return ctx


class SupportAssetCreateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, CreatedByMixin, CreateView):
    model = SupportAsset
    form_class = SupportAssetCreateForm
    template_name = "assets/support_asset_form.html"
    permission_required = "assets.support_asset.create"
    modal_template_name = "assets/support_asset_form_modal.html"
    modal_title_create = _l("New support asset")
    modal_title_update = _l("Edit support asset")
    success_url = reverse_lazy("assets:support-asset-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class SupportAssetUpdateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, ApprovableUpdateMixin, ScopeFilterMixin, UpdateView):
    model = SupportAsset
    form_class = SupportAssetUpdateForm
    template_name = "assets/support_asset_form.html"
    permission_required = "assets.support_asset.update"
    modal_template_name = "assets/support_asset_form_modal.html"
    modal_title_create = _l("New support asset")
    modal_title_update = _l("Edit support asset")
    success_url = reverse_lazy("assets:support-asset-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class SupportAssetDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = SupportAsset
    template_name = "assets/confirm_delete.html"
    permission_required = "assets.support_asset.delete"
    success_url = reverse_lazy("assets:support-asset-list")


# ── Dependency ──────────────────────────────────────────────

class DependencyListView(LoginRequiredMixin, PermissionRequiredMixin, SortableListMixin, ListView):
    model = AssetDependency
    template_name = "assets/dependency_list.html"
    context_object_name = "dependencies"
    permission_required = "assets.dependency.read"
    paginate_by = 25
    sortable_fields = {
        "reference": "reference",
        "essential": "essential_asset__name",
        "support": "support_asset__name",
        "type": "dependency_type",
        "criticality": "criticality",
        "workflow_state": "workflow_state",
    }
    default_sort = "reference"
    search_fields = ["reference", "essential_asset__name", "support_asset__name"]

    def get_queryset(self):
        return super().get_queryset().select_related(
            "essential_asset", "support_asset"
        )


class DependencyCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreatedByMixin, CreateView):
    model = AssetDependency
    form_class = AssetDependencyForm
    template_name = "assets/dependency_form.html"
    permission_required = "assets.dependency.create"
    success_url = reverse_lazy("assets:dependency-list")


class DependencyUpdateView(LoginRequiredMixin, PermissionRequiredMixin, ApprovableUpdateMixin, UpdateView):
    model = AssetDependency
    form_class = AssetDependencyForm
    template_name = "assets/dependency_form.html"
    permission_required = "assets.dependency.update"
    success_url = reverse_lazy("assets:dependency-list")


class DependencyDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = AssetDependency
    template_name = "assets/confirm_delete.html"
    permission_required = "assets.dependency.delete"
    success_url = reverse_lazy("assets:dependency-list")


# ── Group ───────────────────────────────────────────────────

class GroupListView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = AssetGroup
    template_name = "assets/group_list.html"
    context_object_name = "groups"
    permission_required = "assets.group.read"
    paginate_by = 25
    sortable_fields = {
        "reference": "reference",
        "name": "name",
        "type": "type",
        "workflow_state": "workflow_state",
    }
    default_sort = "reference"
    search_fields = ["reference", "name"]

    def get_queryset(self):
        return super().get_queryset().annotate(
            member_count=Count("members")
        )


class GroupDetailView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, ApprovalContextMixin, HistoryMixin, WorkflowStepperMixin, DetailView):
    model = AssetGroup
    template_name = "assets/group_detail.html"
    context_object_name = "group"
    permission_required = "assets.group.read"
    approval_feature = "group"
    approve_url_name = "assets:group-approve"

    def get_queryset(self):
        return super().get_queryset().prefetch_related("members")


class GroupCreateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, CreatedByMixin, CreateView):
    model = AssetGroup
    form_class = AssetGroupCreateForm
    template_name = "assets/group_form.html"
    permission_required = "assets.group.create"
    modal_template_name = "assets/group_form_modal.html"
    modal_title_create = _l("New asset group")
    modal_title_update = _l("Edit asset group")
    success_url = reverse_lazy("assets:group-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class GroupUpdateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, ApprovableUpdateMixin, ScopeFilterMixin, UpdateView):
    model = AssetGroup
    form_class = AssetGroupUpdateForm
    template_name = "assets/group_form.html"
    permission_required = "assets.group.update"
    modal_template_name = "assets/group_form_modal.html"
    modal_title_create = _l("New asset group")
    modal_title_update = _l("Edit asset group")
    success_url = reverse_lazy("assets:group-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class GroupDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = AssetGroup
    template_name = "assets/confirm_delete.html"
    permission_required = "assets.group.delete"
    success_url = reverse_lazy("assets:group-list")


# ── Supplier ──────────────────────────────────────────────

class SupplierListView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = Supplier
    template_name = "assets/supplier_list.html"
    context_object_name = "suppliers"
    permission_required = "assets.supplier.read"
    paginate_by = 25
    sortable_fields = {
        "reference": "reference",
        "name": "name",
        "criticality": "criticality",
        "contract_end": "contract_end_date",
        "workflow_state": "workflow_state",
    }
    default_sort = "reference"
    search_fields = ["reference", "name", "contact_name"]

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related("scopes").select_related("owner", "type")
        supplier_type = self.request.GET.get("type")
        if supplier_type:
            qs = qs.filter(type_id=supplier_type)
        status_filter = self.request.GET.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


class SupplierDetailView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, ApprovalContextMixin, HistoryMixin, WorkflowStepperMixin, DetailView):
    model = Supplier
    template_name = "assets/supplier_detail.html"
    context_object_name = "supplier"
    permission_required = "assets.supplier.read"
    approval_feature = "supplier"
    approve_url_name = "assets:supplier-approve"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["requirements"] = self.object.requirements.select_related(
            "requirement", "verified_by"
        )
        ctx["compliance_summary"] = self.object.requirement_compliance_summary
        if self.object.type:
            ctx["type_requirements"] = self.object.type.requirements.all()
        else:
            ctx["type_requirements"] = []
        return ctx


class SupplierCreateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, CreatedByMixin, CreateView):
    model = Supplier
    form_class = SupplierCreateForm
    template_name = "assets/supplier_form.html"
    permission_required = "assets.supplier.create"
    modal_template_name = "assets/supplier_form_modal.html"
    modal_title_create = _l("New supplier")
    modal_title_update = _l("Edit supplier")
    success_url = reverse_lazy("assets:supplier-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class SupplierUpdateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, ApprovableUpdateMixin, ScopeFilterMixin, UpdateView):
    model = Supplier
    form_class = SupplierUpdateForm
    template_name = "assets/supplier_form.html"
    permission_required = "assets.supplier.update"
    modal_template_name = "assets/supplier_form_modal.html"
    modal_title_create = _l("New supplier")
    modal_title_update = _l("Edit supplier")
    success_url = reverse_lazy("assets:supplier-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class SupplierDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Supplier
    template_name = "assets/confirm_delete.html"
    permission_required = "assets.supplier.delete"
    success_url = reverse_lazy("assets:supplier-list")


class SupplierArchiveView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Archive a supplier (set status to 'archived')."""

    permission_required = "assets.supplier.update"

    def post(self, request, pk):
        supplier = get_object_or_404(Supplier, pk=pk)
        supplier.status = "archived"
        supplier.save(update_fields=["status"])
        messages.success(request, _("Supplier archived."))
        return redirect("assets:supplier-list")


# ── Supplier Types ────────────────────────────────────────


class SupplierTypeListView(LoginRequiredMixin, PermissionRequiredMixin, SortableListMixin, ListView):
    model = SupplierType
    template_name = "assets/supplier_type_list.html"
    context_object_name = "supplier_types"
    permission_required = "assets.supplier.read"
    sortable_fields = {"name": "name"}
    default_sort = "name"
    search_fields = ["name"]


class SupplierTypeDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = SupplierType
    template_name = "assets/supplier_type_detail.html"
    context_object_name = "supplier_type"
    permission_required = "assets.supplier.read"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["requirements"] = self.object.requirements.all()
        ctx["suppliers"] = self.object.suppliers.prefetch_related("scopes").select_related("owner")
        return ctx


class SupplierTypeFormsetMixin:
    """Handle the requirements inline formset for SupplierType create/update."""

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx["requirement_formset"] = SupplierTypeRequirementFormSet(
                self.request.POST, instance=self.object
            )
        else:
            ctx["requirement_formset"] = SupplierTypeRequirementFormSet(
                instance=self.object
            )
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        formset = ctx["requirement_formset"]
        if formset.is_valid():
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            return redirect(self.get_success_url())
        return self.render_to_response(ctx)


class SupplierTypeCreateView(LoginRequiredMixin, PermissionRequiredMixin, SupplierTypeFormsetMixin, CreateView):
    model = SupplierType
    form_class = SupplierTypeForm
    template_name = "assets/supplier_type_form.html"
    permission_required = "assets.supplier.create"
    success_url = reverse_lazy("assets:supplier-type-list")


class SupplierTypeUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SupplierTypeFormsetMixin, UpdateView):
    model = SupplierType
    form_class = SupplierTypeForm
    template_name = "assets/supplier_type_form.html"
    permission_required = "assets.supplier.update"
    success_url = reverse_lazy("assets:supplier-type-list")


class SupplierTypeDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = SupplierType
    template_name = "assets/confirm_delete.html"
    permission_required = "assets.supplier.delete"
    success_url = reverse_lazy("assets:supplier-type-list")


# ── Supplier Type Requirements ───────────────────────────

class SupplierTypeRequirementCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = SupplierTypeRequirement
    form_class = SupplierTypeRequirementForm
    template_name = "assets/supplier_type_requirement_form.html"
    permission_required = "assets.supplier.create"

    def dispatch(self, request, *args, **kwargs):
        self.supplier_type = get_object_or_404(SupplierType, pk=kwargs["type_pk"])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.supplier_type = self.supplier_type
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["supplier_type"] = self.supplier_type
        return ctx

    def get_success_url(self):
        return reverse_lazy("assets:supplier-type-detail", kwargs={"pk": self.supplier_type.pk})


class SupplierTypeRequirementUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = SupplierTypeRequirement
    form_class = SupplierTypeRequirementForm
    template_name = "assets/supplier_type_requirement_form.html"
    permission_required = "assets.supplier.update"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["supplier_type"] = self.object.supplier_type
        return ctx

    def get_success_url(self):
        return reverse_lazy("assets:supplier-type-detail", kwargs={"pk": self.object.supplier_type.pk})


class SupplierTypeRequirementDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = SupplierTypeRequirement
    template_name = "assets/confirm_delete.html"
    permission_required = "assets.supplier.delete"

    def get_success_url(self):
        return reverse_lazy("assets:supplier-type-detail", kwargs={"pk": self.object.supplier_type.pk})


# ── Supplier Requirements ─────────────────────────────────

class SupplierRequirementCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = SupplierRequirement
    form_class = SupplierRequirementForm
    template_name = "assets/supplier_requirement_form.html"
    permission_required = "assets.supplier.create"

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


class SupplierRequirementUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = SupplierRequirement
    form_class = SupplierRequirementForm
    template_name = "assets/supplier_requirement_form.html"
    permission_required = "assets.supplier.update"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["supplier"] = self.object.supplier
        return ctx

    def get_success_url(self):
        return reverse_lazy("assets:supplier-detail", kwargs={"pk": self.object.supplier.pk})


class SupplierRequirementDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = SupplierRequirement
    template_name = "assets/confirm_delete.html"
    permission_required = "assets.supplier.delete"

    def get_success_url(self):
        return reverse_lazy("assets:supplier-detail", kwargs={"pk": self.object.supplier.pk})


class SupplierRequirementDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = SupplierRequirement
    template_name = "assets/supplier_requirement_detail.html"
    context_object_name = "req"
    permission_required = "assets.supplier.read"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["supplier"] = self.object.supplier
        ctx["reviews"] = self.object.reviews.select_related("reviewer")
        return ctx


# ── Supplier Requirement Reviews ──────────────────────────

class SupplierRequirementReviewCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = SupplierRequirementReview
    form_class = SupplierRequirementReviewForm
    template_name = "assets/supplier_requirement_review_form.html"
    permission_required = "assets.supplier.create"

    def dispatch(self, request, *args, **kwargs):
        self.supplier_requirement = get_object_or_404(
            SupplierRequirement, pk=kwargs["requirement_pk"]
        )
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.supplier_requirement = self.supplier_requirement
        form.instance.reviewer = self.request.user
        response = super().form_valid(form)
        # Update the requirement's compliance status from the review
        req = self.supplier_requirement
        req.compliance_status = form.instance.result
        req.verified_at = timezone.now()
        req.verified_by = self.request.user
        req.save(update_fields=["compliance_status", "verified_at", "verified_by"])
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["supplier_requirement"] = self.supplier_requirement
        ctx["supplier"] = self.supplier_requirement.supplier
        return ctx

    def get_success_url(self):
        return reverse_lazy(
            "assets:supplier-requirement-detail",
            kwargs={"pk": self.supplier_requirement.pk},
        )


class SupplierRequirementReviewDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = SupplierRequirementReview
    template_name = "assets/confirm_delete.html"
    permission_required = "assets.supplier.delete"

    def get_success_url(self):
        return reverse_lazy(
            "assets:supplier-requirement-detail",
            kwargs={"pk": self.object.supplier_requirement.pk},
        )


class InstantiateTypeRequirementReviewView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Get-or-create a SupplierRequirement from a type requirement, then redirect to the review form."""

    permission_required = "assets.supplier.create"

    def post(self, request, supplier_pk, type_req_pk):
        supplier = get_object_or_404(Supplier, pk=supplier_pk)
        type_req = get_object_or_404(SupplierTypeRequirement, pk=type_req_pk)

        req, _created = SupplierRequirement.objects.get_or_create(
            supplier=supplier,
            source_type_requirement=type_req,
            defaults={
                "title": type_req.title,
                "description": type_req.description,
            },
        )
        return redirect(
            "assets:supplier-requirement-review-create",
            requirement_pk=req.pk,
        )


# ── Supplier Dependencies ─────────────────────────────────

class SupplierDependencyListView(LoginRequiredMixin, PermissionRequiredMixin, SortableListMixin, ListView):
    model = SupplierDependency
    template_name = "assets/supplier_dependency_list.html"
    context_object_name = "dependencies"
    permission_required = "assets.supplier_dependency.read"
    paginate_by = 25
    sortable_fields = {
        "reference": "reference",
        "support": "support_asset__name",
        "supplier": "supplier__name",
        "type": "dependency_type",
        "criticality": "criticality",
        "workflow_state": "workflow_state",
    }
    default_sort = "reference"
    search_fields = ["reference", "support_asset__name", "supplier__name"]

    def get_queryset(self):
        return super().get_queryset().select_related(
            "support_asset", "supplier"
        )


class SupplierDependencyCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreatedByMixin, CreateView):
    model = SupplierDependency
    form_class = SupplierDependencyForm
    template_name = "assets/supplier_dependency_form.html"
    permission_required = "assets.supplier_dependency.create"
    success_url = reverse_lazy("assets:supplier-dependency-list")


class SupplierDependencyUpdateView(LoginRequiredMixin, PermissionRequiredMixin, ApprovableUpdateMixin, UpdateView):
    model = SupplierDependency
    form_class = SupplierDependencyForm
    template_name = "assets/supplier_dependency_form.html"
    permission_required = "assets.supplier_dependency.update"
    success_url = reverse_lazy("assets:supplier-dependency-list")


class SupplierDependencyDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = SupplierDependency
    template_name = "assets/confirm_delete.html"
    permission_required = "assets.supplier_dependency.delete"
    success_url = reverse_lazy("assets:supplier-dependency-list")


# ── Sites ─────────────────────────────────────────────────

class SiteListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Site
    template_name = "assets/site_list.html"
    context_object_name = "sites"
    permission_required = "context.site.read"

    def get_queryset(self):
        return super().get_queryset().select_related("parent_site")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["sites"] = self._build_tree(list(ctx["sites"]))
        return ctx

    @staticmethod
    def _build_tree(sites):
        by_parent = {}
        for s in sites:
            by_parent.setdefault(s.parent_site_id, []).append(s)
        result = []
        visited = set()

        def walk(parent_id, level):
            for s in by_parent.get(parent_id, []):
                s.tree_level = level
                s.tree_indent = level * 24
                result.append(s)
                visited.add(s.pk)
                walk(s.pk, level + 1)

        walk(None, 0)
        for s in sites:
            if s.pk not in visited:
                s.tree_level = 0
                s.tree_indent = 0
                result.append(s)
        return result


class SiteDetailView(LoginRequiredMixin, PermissionRequiredMixin, ApprovalContextMixin, HistoryMixin, WorkflowStepperMixin, DetailView):
    model = Site
    template_name = "assets/site_detail.html"
    context_object_name = "site"
    permission_required = "context.site.read"
    approve_url_name = "assets:site-approve"

    def get_queryset(self):
        return super().get_queryset().select_related("parent_site")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["ancestors"] = self.object.get_ancestors()
        ctx["children"] = self.object.children.exclude(workflow_state="archived")
        return ctx


class SiteCreateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, CreatedByMixin, CreateView):
    model = Site
    form_class = SiteCreateForm
    template_name = "assets/site_form.html"
    permission_required = "context.site.create"
    modal_template_name = "assets/site_form_modal.html"
    modal_title_create = _l("New site")
    modal_title_update = _l("Edit site")
    success_url = reverse_lazy("assets:site-list")


class SiteUpdateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, ApprovableUpdateMixin, UpdateView):
    model = Site
    form_class = SiteUpdateForm
    template_name = "assets/site_form.html"
    permission_required = "context.site.update"
    modal_template_name = "assets/site_form_modal.html"
    modal_title_create = _l("New site")
    modal_title_update = _l("Edit site")
    success_url = reverse_lazy("assets:site-list")


class SiteDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Site
    template_name = "assets/confirm_delete.html"
    permission_required = "context.site.delete"
    success_url = reverse_lazy("assets:site-list")


# ── Site–Asset Dependencies ──────────────────────────────

class SiteAssetDependencyListView(LoginRequiredMixin, PermissionRequiredMixin, SortableListMixin, ListView):
    model = SiteAssetDependency
    template_name = "assets/site_asset_dependency_list.html"
    context_object_name = "dependencies"
    permission_required = "assets.dependency.read"
    paginate_by = 25
    sortable_fields = {
        "reference": "reference",
        "support": "support_asset__name",
        "site": "site__name",
        "type": "dependency_type",
        "criticality": "criticality",
        "workflow_state": "workflow_state",
    }
    default_sort = "reference"
    search_fields = ["reference", "support_asset__name", "site__name"]

    def get_queryset(self):
        return super().get_queryset().select_related("support_asset", "site")


class SiteAssetDependencyCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreatedByMixin, CreateView):
    model = SiteAssetDependency
    form_class = SiteAssetDependencyForm
    template_name = "assets/site_asset_dependency_form.html"
    permission_required = "assets.dependency.create"
    success_url = reverse_lazy("assets:site-asset-dependency-list")


class SiteAssetDependencyUpdateView(LoginRequiredMixin, PermissionRequiredMixin, ApprovableUpdateMixin, UpdateView):
    model = SiteAssetDependency
    form_class = SiteAssetDependencyForm
    permission_required = "assets.dependency.update"
    template_name = "assets/site_asset_dependency_form.html"
    success_url = reverse_lazy("assets:site-asset-dependency-list")


class SiteAssetDependencyDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = SiteAssetDependency
    template_name = "assets/confirm_delete.html"
    permission_required = "assets.dependency.delete"
    success_url = reverse_lazy("assets:site-asset-dependency-list")


# ── Site–Supplier Dependencies ───────────────────────────

class SiteSupplierDependencyListView(LoginRequiredMixin, PermissionRequiredMixin, SortableListMixin, ListView):
    model = SiteSupplierDependency
    template_name = "assets/site_supplier_dependency_list.html"
    context_object_name = "dependencies"
    permission_required = "assets.supplier_dependency.read"
    paginate_by = 25
    sortable_fields = {
        "reference": "reference",
        "site": "site__name",
        "supplier": "supplier__name",
        "type": "dependency_type",
        "criticality": "criticality",
        "workflow_state": "workflow_state",
    }
    default_sort = "reference"
    search_fields = ["reference", "site__name", "supplier__name"]

    def get_queryset(self):
        return super().get_queryset().select_related("site", "supplier")


class SiteSupplierDependencyCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreatedByMixin, CreateView):
    model = SiteSupplierDependency
    form_class = SiteSupplierDependencyForm
    template_name = "assets/site_supplier_dependency_form.html"
    permission_required = "assets.supplier_dependency.create"
    success_url = reverse_lazy("assets:site-supplier-dependency-list")


class SiteSupplierDependencyUpdateView(LoginRequiredMixin, PermissionRequiredMixin, ApprovableUpdateMixin, UpdateView):
    model = SiteSupplierDependency
    form_class = SiteSupplierDependencyForm
    template_name = "assets/site_supplier_dependency_form.html"
    permission_required = "assets.supplier_dependency.update"
    success_url = reverse_lazy("assets:site-supplier-dependency-list")


class SiteSupplierDependencyDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = SiteSupplierDependency
    template_name = "assets/confirm_delete.html"
    permission_required = "assets.supplier_dependency.delete"
    success_url = reverse_lazy("assets:site-supplier-dependency-list")


# ── Dependency Graph ──────────────────────────────────────

class DependencyGraphView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = "assets/dependency_graph.html"
    permission_required = "assets.dependency.read"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Asset dependencies (essential → support)
        asset_deps = AssetDependency.objects.select_related(
            "essential_asset", "support_asset"
        ).all()
        # Supplier dependencies (support → supplier)
        supplier_deps = SupplierDependency.objects.select_related(
            "support_asset", "supplier"
        ).all()
        # Site–asset dependencies (support → site)
        site_asset_deps = SiteAssetDependency.objects.select_related(
            "support_asset", "site"
        ).all()
        # Site–supplier dependencies (site → supplier)
        site_supplier_deps = SiteSupplierDependency.objects.select_related(
            "site", "supplier"
        ).all()

        nodes = {}
        edges = []

        for dep in asset_deps:
            ea = dep.essential_asset
            sa = dep.support_asset
            ea_id = str(ea.id)
            sa_id = str(sa.id)
            if ea_id not in nodes:
                nodes[ea_id] = {
                    "id": ea_id,
                    "label": f"{ea.reference} - {ea.name}",
                    "type": "essential",
                }
            if sa_id not in nodes:
                nodes[sa_id] = {
                    "id": sa_id,
                    "label": f"{sa.reference} - {sa.name}",
                    "type": "support",
                }
            edges.append({
                "source": ea_id,
                "target": sa_id,
                "label": dep.get_dependency_type_display(),
                "criticality": dep.criticality,
                "is_spof": dep.is_single_point_of_failure,
                "kind": "asset",
            })

        for dep in supplier_deps:
            sa = dep.support_asset
            sup = dep.supplier
            sa_id = str(sa.id)
            sup_id = str(sup.id)
            if sa_id not in nodes:
                nodes[sa_id] = {
                    "id": sa_id,
                    "label": f"{sa.reference} - {sa.name}",
                    "type": "support",
                }
            if sup_id not in nodes:
                nodes[sup_id] = {
                    "id": sup_id,
                    "label": f"{sup.reference} - {sup.name}",
                    "type": "supplier",
                    "logo": sup.logo_64 or sup.logo or "",
                }
            edges.append({
                "source": sa_id,
                "target": sup_id,
                "label": dep.get_dependency_type_display(),
                "criticality": dep.criticality,
                "is_spof": dep.is_single_point_of_failure,
                "kind": "supplier",
            })

        for dep in site_asset_deps:
            sa = dep.support_asset
            site = dep.site
            sa_id = str(sa.id)
            site_id = str(site.id)
            if sa_id not in nodes:
                nodes[sa_id] = {
                    "id": sa_id,
                    "label": f"{sa.reference} - {sa.name}",
                    "type": "support",
                }
            if site_id not in nodes:
                nodes[site_id] = {
                    "id": site_id,
                    "label": f"{site.reference} - {site.name}",
                    "type": "site",
                }
            edges.append({
                "source": sa_id,
                "target": site_id,
                "label": dep.get_dependency_type_display(),
                "criticality": dep.criticality,
                "is_spof": dep.is_single_point_of_failure,
                "kind": "site",
            })

        for dep in site_supplier_deps:
            site = dep.site
            sup = dep.supplier
            site_id = str(site.id)
            sup_id = str(sup.id)
            if site_id not in nodes:
                nodes[site_id] = {
                    "id": site_id,
                    "label": f"{site.reference} - {site.name}",
                    "type": "site",
                }
            if sup_id not in nodes:
                nodes[sup_id] = {
                    "id": sup_id,
                    "label": f"{sup.reference} - {sup.name}",
                    "type": "supplier",
                    "logo": sup.logo_64 or sup.logo or "",
                }
            edges.append({
                "source": site_id,
                "target": sup_id,
                "label": dep.get_dependency_type_display(),
                "criticality": dep.criticality,
                "is_spof": dep.is_single_point_of_failure,
                "kind": "site_supplier",
            })

        import json
        ctx["graph_nodes"] = json.dumps(list(nodes.values()))
        ctx["graph_edges"] = json.dumps(edges)
        ctx["asset_dep_count"] = asset_deps.count()
        ctx["supplier_dep_count"] = supplier_deps.count()
        ctx["site_asset_dep_count"] = site_asset_deps.count()
        ctx["site_supplier_dep_count"] = site_supplier_deps.count()
        return ctx
