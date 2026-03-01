from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Avg, Count, Prefetch, Q
from django.http import JsonResponse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import TemplateView

from assets.models import (
    AssetDependency,
    AssetGroup,
    EssentialAsset,
    Supplier,
    SupplierDependency,
    SupplierRequirementReview,
    SupplierType,
    SupportAsset,
)
from compliance.models import (
    ComplianceActionPlan,
    ComplianceAssessment,
    Framework,
    Requirement,
    RequirementMapping,
)
from context.models import Activity, Issue, Objective, Role, Scope, Site, Stakeholder, SwotAnalysis
from risks.models import (
    Risk,
    RiskAcceptance,
    RiskAssessment,
    RiskCriteria,
    RiskTreatmentPlan,
    Threat,
    Vulnerability,
)
from risks.views import build_default_risk_matrix, build_risk_matrix


class GeneralDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "home.html"

    def _scope_ids(self):
        user = self.request.user
        if user.is_superuser:
            return None
        return user.get_allowed_scope_ids()

    def _filter_scoped(self, qs):
        scope_ids = self._scope_ids()
        if scope_ids is None:
            return qs
        model = qs.model
        if hasattr(model, "scope"):
            return qs.filter(scope_id__in=scope_ids)
        if model._meta.many_to_many and any(
            f.name == "scopes" for f in model._meta.many_to_many
        ):
            return qs.filter(scopes__id__in=scope_ids).distinct()
        return qs

    def _filter_scopes(self, qs):
        scope_ids = self._scope_ids()
        if scope_ids is None:
            return qs
        return qs.filter(id__in=scope_ids)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.now().date()

        # ── Gouvernance ──────────────────────────────────
        scopes = self._filter_scopes(Scope.objects.all())
        ctx["scope_count"] = scopes.count()
        ctx["active_scopes"] = scopes.filter(status="active").select_related("parent_scope")[:5]
        ctx["issue_count"] = self._filter_scoped(Issue.objects.all()).count()
        ctx["stakeholder_count"] = self._filter_scoped(Stakeholder.objects.all()).count()
        ctx["objective_count"] = self._filter_scoped(Objective.objects.all()).count()
        ctx["role_count"] = self._filter_scoped(Role.objects.all()).count()
        ctx["site_count"] = Site.objects.count()
        ctx["mandatory_roles_no_user"] = self._filter_scoped(
            Role.objects.filter(is_mandatory=True)
        ).annotate(user_count=Count("assigned_users")).filter(user_count=0).count()
        ctx["swot_count"] = self._filter_scoped(SwotAnalysis.objects.all()).count()
        ctx["activity_count"] = self._filter_scoped(Activity.objects.all()).count()
        ctx["critical_activities_no_owner"] = self._filter_scoped(
            Activity.objects.filter(criticality="critical", owner__isnull=True)
        ).count()

        # ── Actifs ──────────────────────────────────────
        ctx["essential_count"] = EssentialAsset.objects.count()
        ctx["support_count"] = SupportAsset.objects.count()
        ctx["dependency_count"] = AssetDependency.objects.count()
        ctx["spof_count"] = (
            AssetDependency.objects.filter(is_single_point_of_failure=True).count()
            + SupplierDependency.objects.filter(is_single_point_of_failure=True).count()
        )
        ctx["eol_count"] = SupportAsset.objects.filter(
            end_of_life_date__lte=today, status="active"
        ).count()
        ctx["personal_data_count"] = EssentialAsset.objects.filter(
            personal_data=True
        ).count()
        ctx["supplier_count"] = Supplier.objects.count()
        ctx["expired_contract_count"] = Supplier.objects.filter(
            contract_end_date__lt=today, status="active"
        ).count()
        ctx["supplier_dep_count"] = SupplierDependency.objects.count()
        ctx["supplier_spof_count"] = SupplierDependency.objects.filter(
            is_single_point_of_failure=True
        ).count()
        ctx["supplier_type_count"] = SupplierType.objects.count()
        ctx["group_count"] = AssetGroup.objects.count()

        # ── Gestion des risques ─────────────────────────
        ctx["risk_assessment_count"] = self._filter_scoped(
            RiskAssessment.objects.all()
        ).count()
        ctx["risk_count"] = Risk.objects.count()
        ctx["treatment_plan_count"] = RiskTreatmentPlan.objects.count()
        ctx["treatment_in_progress_count"] = RiskTreatmentPlan.objects.filter(
            status="in_progress"
        ).count()
        ctx["critical_risk_count"] = Risk.objects.filter(
            priority="critical"
        ).count()
        ctx["acceptance_count"] = RiskAcceptance.objects.filter(
            status="active"
        ).count()
        ctx["expiring_acceptance_count"] = RiskAcceptance.objects.filter(
            status="active",
            valid_until__lte=today + timedelta(days=30),
            valid_until__gte=today,
        ).count()
        ctx["threat_count"] = Threat.objects.count()
        ctx["vulnerability_count"] = Vulnerability.objects.count()

        # Risk matrices
        criteria = RiskCriteria.objects.filter(is_default=True).first()
        if not criteria:
            criteria = RiskCriteria.objects.filter(status="active").first()
        all_risks = Risk.objects.all()
        if criteria:
            ctx["matrix_criteria"] = criteria
            ctx["matrix_current"] = build_risk_matrix(
                all_risks, criteria, "current_likelihood", "current_impact"
            )
            ctx["matrix_residual"] = build_risk_matrix(
                all_risks, criteria, "residual_likelihood", "residual_impact"
            )
        # Fallback to default 5×5 matrix if no criteria or build returned None
        if not ctx.get("matrix_current"):
            ctx["matrix_current"] = build_default_risk_matrix(
                all_risks, "current_likelihood", "current_impact"
            )
        if not ctx.get("matrix_residual"):
            ctx["matrix_residual"] = build_default_risk_matrix(
                all_risks, "residual_likelihood", "residual_impact"
            )

        # ── Conformité ───────────────────────────────────
        frameworks = self._filter_scoped(Framework.objects.all())
        ctx["framework_count"] = frameworks.count()
        active_frameworks = self._filter_scoped(
            Framework.objects.filter(status="active")
        ).select_related("owner").prefetch_related(
            Prefetch("scopes", queryset=Scope.objects.select_related("parent_scope")),
        ).annotate(
            req_count=Count("requirements", filter=Q(requirements__is_applicable=True)),
        )[:10]
        ctx["active_frameworks"] = active_frameworks

        # Overall compliance: weighted average by applicable requirement count
        agg = self._filter_scoped(
            Framework.objects.filter(status="active")
        ).aggregate(avg=Avg("compliance_level"))
        ctx["overall_compliance"] = round(agg["avg"] or 0)

        ctx["requirement_count"] = Requirement.objects.count()
        ctx["non_compliant_count"] = Requirement.objects.filter(
            compliance_status="non_compliant"
        ).count()
        ctx["assessment_count"] = self._filter_scoped(
            ComplianceAssessment.objects.all()
        ).count()
        ctx["action_plan_count"] = self._filter_scoped(
            ComplianceActionPlan.objects.all()
        ).count()
        ctx["overdue_plan_count"] = self._filter_scoped(
            ComplianceActionPlan.objects.filter(
                target_date__lt=today
            ).exclude(status__in=["completed", "cancelled"])
        ).count()
        ctx["mapping_count"] = RequirementMapping.objects.count()

        # ── Global alerts ─────────────────────────────
        alerts = []
        if ctx["mandatory_roles_no_user"]:
            alerts.append(
                _("%(count)d mandatory role(s) with no assigned user")
                % {"count": ctx["mandatory_roles_no_user"]}
            )
        if ctx["spof_count"]:
            alerts.append(
                _("%(count)d single point(s) of failure (SPOF)")
                % {"count": ctx["spof_count"]}
            )
        if ctx["eol_count"]:
            alerts.append(
                _("%(count)d support asset(s) past end of life")
                % {"count": ctx["eol_count"]}
            )
        if ctx["non_compliant_count"]:
            alerts.append(
                _("%(count)d non-compliant requirement(s)")
                % {"count": ctx["non_compliant_count"]}
            )
        if ctx["overdue_plan_count"]:
            alerts.append(
                _("%(count)d overdue action plan(s)")
                % {"count": ctx["overdue_plan_count"]}
            )
        if ctx["critical_risk_count"]:
            alerts.append(
                _("%(count)d critical risk(s)")
                % {"count": ctx["critical_risk_count"]}
            )
        if ctx["expired_contract_count"]:
            alerts.append(
                _("%(count)d supplier(s) with expired contract")
                % {"count": ctx["expired_contract_count"]}
            )
        if ctx["expiring_acceptance_count"]:
            alerts.append(
                _("%(count)d risk acceptance(s) expiring within 30 days")
                % {"count": ctx["expiring_acceptance_count"]}
            )
        if ctx["critical_activities_no_owner"]:
            alerts.append(
                _("%(count)d critical activity(ies) without owner")
                % {"count": ctx["critical_activities_no_owner"]}
            )
        ctx["alerts"] = alerts

        return ctx


class CalendarView(LoginRequiredMixin, TemplateView):
    template_name = "calendar.html"


class CalendarEventsView(LoginRequiredMixin, View):
    """Return calendar events as JSON for FullCalendar."""

    def _scope_ids(self):
        user = self.request.user
        if user.is_superuser:
            return None
        return user.get_allowed_scope_ids()

    def _filter_scoped(self, qs):
        scope_ids = self._scope_ids()
        if scope_ids is None:
            return qs
        model = qs.model
        if hasattr(model, "scope"):
            return qs.filter(scope_id__in=scope_ids)
        if model._meta.many_to_many and any(
            f.name == "scopes" for f in model._meta.many_to_many
        ):
            return qs.filter(scopes__id__in=scope_ids).distinct()
        return qs

    def get(self, request):
        start = request.GET.get("start")
        end = request.GET.get("end")
        categories = request.GET.getlist("categories")

        events = []
        if not categories:
            categories = [
                "risk_assessment", "compliance_assessment", "action_plan",
                "treatment_plan", "scope", "objective", "framework", "swot",
                "acceptance", "supplier_review",
            ]

        def add_events(queryset, date_field, category, color, url_name, label_prefix=""):
            filters = {}
            if start:
                filters[f"{date_field}__gte"] = start
            if end:
                filters[f"{date_field}__lte"] = end
            filters[f"{date_field}__isnull"] = False
            qs = queryset.filter(**filters)
            for obj in qs:
                date_val = getattr(obj, date_field)
                title = str(obj)
                if label_prefix:
                    title = f"{label_prefix}{title}"
                events.append({
                    "title": title,
                    "start": date_val.isoformat(),
                    "color": color,
                    "category": category,
                    "url": self._get_url(obj, url_name),
                })

        # ── Risk assessments ──────────────────────────────
        if "risk_assessment" in categories:
            qs = self._filter_scoped(RiskAssessment.objects.all())
            add_events(qs, "assessment_date", "risk_assessment", "#ef4444",
                       "risks:assessment-detail")
            add_events(qs, "next_review_date", "risk_assessment", "#fca5a5",
                       "risks:assessment-detail", _("Review: "))

        # ── Compliance assessments ────────────────────────
        if "compliance_assessment" in categories:
            qs = self._filter_scoped(ComplianceAssessment.objects.all())
            add_events(qs, "assessment_date", "compliance_assessment", "#6366f1",
                       "compliance:assessment-detail")
            add_events(qs, "review_date", "compliance_assessment", "#a5b4fc",
                       "compliance:assessment-detail", _("Review: "))

        # ── Compliance action plans ───────────────────────
        if "action_plan" in categories:
            qs = self._filter_scoped(ComplianceActionPlan.objects.all())
            add_events(qs, "target_date", "action_plan", "#f59e0b",
                       "compliance:action-plan-detail")
            add_events(qs, "start_date", "action_plan", "#fcd34d",
                       "compliance:action-plan-detail", _("Start: "))
            add_events(qs, "completion_date", "action_plan", "#10b981",
                       "compliance:action-plan-detail", _("Done: "))

        # ── Risk treatment plans ──────────────────────────
        if "treatment_plan" in categories:
            qs = RiskTreatmentPlan.objects.all()
            add_events(qs, "target_date", "treatment_plan", "#8b5cf6",
                       "risks:treatment-plan-detail")
            add_events(qs, "start_date", "treatment_plan", "#c4b5fd",
                       "risks:treatment-plan-detail", _("Start: "))
            add_events(qs, "completion_date", "treatment_plan", "#10b981",
                       "risks:treatment-plan-detail", _("Done: "))

        # ── Scopes ────────────────────────────────────────
        if "scope" in categories:
            qs = Scope.objects.all()
            add_events(qs, "effective_date", "scope", "#06b6d4",
                       "context:scope-detail")
            add_events(qs, "review_date", "scope", "#67e8f9",
                       "context:scope-detail", _("Review: "))

        # ── Objectives ────────────────────────────────────
        if "objective" in categories:
            qs = self._filter_scoped(Objective.objects.all())
            add_events(qs, "target_date", "objective", "#14b8a6",
                       "context:objective-detail")
            add_events(qs, "review_date", "objective", "#5eead4",
                       "context:objective-detail", _("Review: "))

        # ── Frameworks ────────────────────────────────────
        if "framework" in categories:
            qs = self._filter_scoped(Framework.objects.all())
            add_events(qs, "effective_date", "framework", "#3b82f6",
                       "compliance:framework-detail")
            add_events(qs, "expiry_date", "framework", "#93c5fd",
                       "compliance:framework-detail", _("Expiry: "))
            add_events(qs, "review_date", "framework", "#bfdbfe",
                       "compliance:framework-detail", _("Review: "))

        # ── SWOT analyses ─────────────────────────────────
        if "swot" in categories:
            qs = self._filter_scoped(SwotAnalysis.objects.all())
            add_events(qs, "analysis_date", "swot", "#ec4899",
                       "context:swot-detail")
            add_events(qs, "review_date", "swot", "#f9a8d4",
                       "context:swot-detail", _("Review: "))

        # ── Risk acceptances ──────────────────────────────
        if "acceptance" in categories:
            qs = RiskAcceptance.objects.all()
            add_events(qs, "valid_until", "acceptance", "#f97316",
                       "risks:acceptance-detail")
            add_events(qs, "review_date", "acceptance", "#fdba74",
                       "risks:acceptance-detail", _("Review: "))

        # ── Supplier requirement reviews ─────────────────
        if "supplier_review" in categories:
            filters = {"review_date__isnull": False}
            if start:
                filters["review_date__gte"] = start
            if end:
                filters["review_date__lte"] = end
            qs = SupplierRequirementReview.objects.select_related(
                "supplier_requirement"
            ).filter(**filters)
            for review in qs:
                events.append({
                    "title": str(review),
                    "start": review.review_date.isoformat(),
                    "color": "#d946ef",
                    "category": "supplier_review",
                    "url": self._get_url(
                        review.supplier_requirement,
                        "assets:supplier-requirement-detail",
                    ),
                })

        return JsonResponse(events, safe=False)

    def _get_url(self, obj, url_name):
        from django.urls import reverse
        try:
            return reverse(url_name, kwargs={"pk": obj.pk})
        except Exception:
            return ""
