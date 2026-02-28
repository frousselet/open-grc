from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Avg, Count, Prefetch, Q
from django.utils import timezone
from django.views.generic import TemplateView

from assets.models import AssetDependency, EssentialAsset, SupportAsset
from compliance.models import (
    ComplianceActionPlan,
    ComplianceAssessment,
    Framework,
    Requirement,
    RequirementMapping,
)
from context.models import Issue, Objective, Role, Scope, Site, Stakeholder
from risks.models import Risk, RiskAssessment, RiskCriteria, RiskTreatmentPlan
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

        # ── Actifs ──────────────────────────────────────
        ctx["essential_count"] = EssentialAsset.objects.count()
        ctx["support_count"] = SupportAsset.objects.count()
        ctx["dependency_count"] = AssetDependency.objects.count()
        ctx["spof_count"] = AssetDependency.objects.filter(
            is_single_point_of_failure=True
        ).count()
        ctx["eol_count"] = SupportAsset.objects.filter(
            end_of_life_date__lte=today, status="active"
        ).count()
        ctx["personal_data_count"] = EssentialAsset.objects.filter(
            personal_data=True
        ).count()

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
        ctx["overall_compliance"] = round(agg["avg"] or 0, 1)

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

        # ── Alertes globales ─────────────────────────────
        alerts = []
        if ctx["mandatory_roles_no_user"]:
            alerts.append(
                f"{ctx['mandatory_roles_no_user']} rôle(s) obligatoire(s) sans utilisateur affecté"
            )
        if ctx["spof_count"]:
            alerts.append(
                f"{ctx['spof_count']} point(s) unique(s) de défaillance (SPOF)"
            )
        if ctx["eol_count"]:
            alerts.append(
                f"{ctx['eol_count']} bien(s) support(s) en fin de vie"
            )
        if ctx["non_compliant_count"]:
            alerts.append(
                f"{ctx['non_compliant_count']} exigence(s) non conforme(s)"
            )
        if ctx["overdue_plan_count"]:
            alerts.append(
                f"{ctx['overdue_plan_count']} plan(s) d'action en retard"
            )
        if ctx["critical_risk_count"]:
            alerts.append(
                f"{ctx['critical_risk_count']} risque(s) critique(s)"
            )
        ctx["alerts"] = alerts

        return ctx
