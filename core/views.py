from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Avg, Count, Max, Prefetch, Q, Subquery, OuterRef
from django.http import JsonResponse
from django.urls import reverse
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
from assets.services.spof_detection import SpofDetector
from compliance.models import (
    ComplianceActionPlan,
    ComplianceAssessment,
    Framework,
    Requirement,
    RequirementMapping,
)
from compliance.models.assessment import AssessmentResult
from context.models import Activity, Indicator, Issue, Objective, Role, Scope, Site, Stakeholder, SwotAnalysis
from context.views import get_dashboard_indicator_slots
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
        if any(f.name == "scopes" for f in model._meta.many_to_many):
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
        ctx["active_objectives"] = self._filter_scoped(
            Objective.objects.filter(status="active")
        ).select_related("owner").prefetch_related(
            Prefetch("scopes", queryset=Scope.objects.select_related("parent_scope")),
        )[:10]
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
        spof_results = SpofDetector().detect_all()
        ctx["spof_count"] = spof_results["total_spof"]
        ctx["spof_detail"] = {
            "asset": len([d for d in spof_results["asset_dependencies"] if d["is_spof"]]),
            "supplier": len([d for d in spof_results["supplier_dependencies"] if d["is_spof"]]),
            "site_asset": len([d for d in spof_results["site_asset_dependencies"] if d["is_spof"]]),
            "site_supplier": len([d for d in spof_results["site_supplier_dependencies"] if d["is_spof"]]),
        }
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
        from compliance.constants import ComplianceStatus as CS

        frameworks = self._filter_scoped(Framework.objects.all())
        ctx["framework_count"] = frameworks.count()
        active_frameworks = list(
            self._filter_scoped(
                Framework.objects.filter(status="active")
            ).select_related("owner").prefetch_related(
                Prefetch("scopes", queryset=Scope.objects.select_related("parent_scope")),
            ).annotate(
                req_count=Count("requirements", filter=Q(requirements__is_applicable=True)),
            )[:10]
        )

        NOT_EVALUATED = {CS.NOT_ASSESSED, CS.EVALUATED}
        COMPLIANT_STATUSES = {CS.COMPLIANT, CS.STRENGTH}
        PARTIAL_STATUSES = {
            CS.MINOR_NON_CONFORMITY, CS.OBSERVATION,
            CS.IMPROVEMENT_OPPORTUNITY,
        }

        # Compute segments from assessment results (latest by end_date, with fallback)
        for fw in active_frameworks:
            rc = fw.req_count or 0
            if rc == 0:
                fw.seg_compliant = fw.seg_partial = fw.seg_non_compliant = 0
                fw.seg_evaluated = fw.seg_not_assessed = 0
                fw.computed_compliance = 0
                continue

            req_ids = set(
                fw.requirements.filter(is_applicable=True).values_list("pk", flat=True)
            )
            all_results = (
                AssessmentResult.objects.filter(
                    assessment__frameworks=fw,
                    requirement_id__in=req_ids,
                )
                .select_related("assessment")
                .order_by("-assessment__assessment_end_date", "-assessment__created_at")
            )

            latest_map = {}    # req_id → (status, level)
            fallback_map = {}  # req_id → (status, level)
            for r in all_results:
                rid = r.requirement_id
                if rid not in latest_map:
                    latest_map[rid] = (r.compliance_status, r.compliance_level)
                if rid not in fallback_map and r.compliance_status not in NOT_EVALUATED:
                    fallback_map[rid] = (r.compliance_status, r.compliance_level)

            counts = {"compliant": 0, "partial": 0, "non_compliant": 0, "evaluated": 0, "not_assessed": 0}
            for rid in req_ids:
                latest = latest_map.get(rid)
                if latest is None:
                    counts["not_assessed"] += 1
                    continue
                status, level = latest
                if status in NOT_EVALUATED:
                    fb = fallback_map.get(rid)
                    if fb:
                        status, level = fb
                    else:
                        status, level = CS.NOT_ASSESSED, 0

                if status == CS.NOT_APPLICABLE:
                    counts["compliant"] += 1
                elif status in COMPLIANT_STATUSES:
                    counts["compliant"] += 1
                elif status in PARTIAL_STATUSES:
                    counts["partial"] += 1
                elif status == CS.MAJOR_NON_CONFORMITY:
                    counts["non_compliant"] += 1
                elif status == CS.EVALUATED:
                    counts["evaluated"] += 1
                else:
                    counts["not_assessed"] += 1

            fw.seg_compliant = round(counts["compliant"] * 100 / rc)
            fw.seg_partial = round(counts["partial"] * 100 / rc)
            fw.seg_non_compliant = round(counts["non_compliant"] * 100 / rc)
            fw.seg_evaluated = round(counts["evaluated"] * 100 / rc)
            fw.seg_not_assessed = round(counts["not_assessed"] * 100 / rc)
            # Compliance % = proportion of compliant requirements (matches green segment)
            fw.computed_compliance = fw.seg_compliant

        ctx["active_frameworks"] = active_frameworks

        # Overall compliance: average of computed framework compliance levels
        if active_frameworks:
            vals = [fw.computed_compliance for fw in active_frameworks]
            ctx["overall_compliance"] = round(sum(vals) / len(vals))
        else:
            ctx["overall_compliance"] = 0

        # Dashboard indicators
        ctx["dashboard_indicator_slots"] = get_dashboard_indicator_slots(self.request.user)
        ctx["available_indicators"] = Indicator.objects.filter(
            status="active",
        ).order_by("indicator_type", "name")
        ctx["dashboard_indicator_chart_ids"] = self.request.user.dashboard_indicator_charts or []

        ctx["requirement_count"] = Requirement.objects.count()
        ctx["non_compliant_count"] = Requirement.objects.filter(
            compliance_status__in=["major_non_conformity", "minor_non_conformity"]
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


class DashboardIndicatorsPartialView(LoginRequiredMixin, TemplateView):
    """Return only the indicators partial for WebSocket-triggered refreshes."""

    template_name = "includes/dashboard_indicators.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["dashboard_indicator_slots"] = get_dashboard_indicator_slots(self.request.user)
        ctx["available_indicators"] = Indicator.objects.filter(
            status="active",
        ).order_by("indicator_type", "name")
        ctx["dashboard_indicator_chart_ids"] = self.request.user.dashboard_indicator_charts or []
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
        if any(f.name == "scopes" for f in model._meta.many_to_many):
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
            add_events(qs, "assessment_start_date", "compliance_assessment", "#6366f1",
                       "compliance:assessment-detail")
            add_events(qs, "assessment_end_date", "compliance_assessment", "#a5b4fc",
                       "compliance:assessment-detail", _("End: "))

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


class GlobalSearchView(LoginRequiredMixin, View):
    """Return search results as JSON, grouped by category."""

    MAX_PER_CATEGORY = 5

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
        if any(f.name == "scopes" for f in model._meta.many_to_many):
            return qs.filter(scopes__id__in=scope_ids).distinct()
        return qs

    def _search_model(self, model, fields, q, url_name, icon):
        """Search a model on the given fields and return result dicts."""
        query = Q()
        for field in fields:
            query |= Q(**{f"{field}__icontains": q})
        qs = model.objects.filter(query)
        qs = self._filter_scoped(qs)
        results = []
        for obj in qs[: self.MAX_PER_CATEGORY]:
            try:
                url = reverse(url_name, kwargs={"pk": obj.pk})
            except Exception:
                url = ""
            results.append({
                "title": str(obj),
                "url": url,
                "icon": icon,
            })
        return results

    def get(self, request):
        q = request.GET.get("q", "").strip()
        if len(q) < 2:
            return JsonResponse({"results": []})

        categories = [
            {
                "label": _("Scopes"),
                "model": Scope,
                "fields": ["name", "reference", "description"],
                "url": "context:scope-detail",
                "icon": "bi-bullseye",
            },
            {
                "label": _("Sites"),
                "model": Site,
                "fields": ["name", "reference"],
                "url": "context:site-detail",
                "icon": "bi-geo-alt",
            },
            {
                "label": _("Objectives"),
                "model": Objective,
                "fields": ["name", "reference", "description"],
                "url": "context:objective-detail",
                "icon": "bi-flag",
            },
            {
                "label": _("Issues"),
                "model": Issue,
                "fields": ["name", "reference", "description"],
                "url": "context:issue-detail",
                "icon": "bi-exclamation-diamond",
            },
            {
                "label": _("Stakeholders"),
                "model": Stakeholder,
                "fields": ["name", "reference"],
                "url": "context:stakeholder-detail",
                "icon": "bi-people",
            },
            {
                "label": _("Roles"),
                "model": Role,
                "fields": ["name", "reference", "description"],
                "url": "context:role-detail",
                "icon": "bi-person-badge",
            },
            {
                "label": _("Activities"),
                "model": Activity,
                "fields": ["name", "reference", "description"],
                "url": "context:activity-detail",
                "icon": "bi-activity",
            },
            {
                "label": _("SWOT Analyses"),
                "model": SwotAnalysis,
                "fields": ["name", "reference"],
                "url": "context:swot-detail",
                "icon": "bi-grid-3x3",
            },
            {
                "label": _("Indicators"),
                "model": Indicator,
                "fields": ["name", "reference", "description"],
                "url": "context:indicator-detail",
                "icon": "bi-speedometer2",
            },
            {
                "label": _("Essential Assets"),
                "model": EssentialAsset,
                "fields": ["name", "reference", "description"],
                "url": "assets:essential-asset-detail",
                "icon": "bi-gem",
            },
            {
                "label": _("Support Assets"),
                "model": SupportAsset,
                "fields": ["name", "reference", "description"],
                "url": "assets:support-asset-detail",
                "icon": "bi-hdd-network",
            },
            {
                "label": _("Asset Groups"),
                "model": AssetGroup,
                "fields": ["name", "reference", "description"],
                "url": "assets:group-detail",
                "icon": "bi-collection",
            },
            {
                "label": _("Suppliers"),
                "model": Supplier,
                "fields": ["name", "reference"],
                "url": "assets:supplier-detail",
                "icon": "bi-truck",
            },
            {
                "label": _("Frameworks"),
                "model": Framework,
                "fields": ["name", "reference", "description"],
                "url": "compliance:framework-detail",
                "icon": "bi-journal-check",
            },
            {
                "label": _("Requirements"),
                "model": Requirement,
                "fields": ["name", "requirement_number", "description"],
                "url": "compliance:requirement-detail",
                "icon": "bi-list-check",
            },
            {
                "label": _("Compliance Assessments"),
                "model": ComplianceAssessment,
                "fields": ["name", "reference"],
                "url": "compliance:assessment-detail",
                "icon": "bi-clipboard-check",
            },
            {
                "label": _("Action Plans"),
                "model": ComplianceActionPlan,
                "fields": ["name", "reference", "description"],
                "url": "compliance:action-plan-detail",
                "icon": "bi-card-checklist",
            },
            {
                "label": _("Risk Assessments"),
                "model": RiskAssessment,
                "fields": ["name", "reference"],
                "url": "risks:assessment-detail",
                "icon": "bi-shield-exclamation",
            },
            {
                "label": _("Risks"),
                "model": Risk,
                "fields": ["name", "reference", "description"],
                "url": "risks:risk-detail",
                "icon": "bi-radioactive",
            },
            {
                "label": _("Threats"),
                "model": Threat,
                "fields": ["name", "reference"],
                "url": "risks:threat-detail",
                "icon": "bi-bug",
            },
            {
                "label": _("Vulnerabilities"),
                "model": Vulnerability,
                "fields": ["name", "reference"],
                "url": "risks:vulnerability-detail",
                "icon": "bi-unlock",
            },
            {
                "label": _("Treatment Plans"),
                "model": RiskTreatmentPlan,
                "fields": ["name", "reference", "description"],
                "url": "risks:treatment-plan-detail",
                "icon": "bi-bandaid",
            },
        ]

        grouped = []
        for cat in categories:
            items = self._search_model(
                cat["model"], cat["fields"], q, cat["url"], cat["icon"],
            )
            if items:
                grouped.append({
                    "label": cat["label"],
                    "icon": cat["icon"],
                    "items": items,
                })

        return JsonResponse({"results": grouped})
