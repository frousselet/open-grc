"""WebSocket consumer for real-time dashboard updates."""

import json
from datetime import timedelta

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.db.models import Avg, Count, Q
from django.utils import timezone


class DashboardConsumer(AsyncWebsocketConsumer):
    """Push dashboard statistics to connected clients in real time.

    Clients connect to ``ws://<host>/ws/dashboard/``.  The consumer joins
    a ``dashboard`` channel-layer group so that any server-side code can
    trigger a refresh by sending::

        async_to_sync(channel_layer.group_send)(
            "dashboard", {"type": "dashboard.refresh"}
        )
    """

    GROUP_NAME = "dashboard"

    async def connect(self):
        user = self.scope.get("user")
        if user is None or user.is_anonymous:
            await self.close()
            return

        await self.channel_layer.group_add(self.GROUP_NAME, self.channel_name)
        await self.accept()

        # Send initial snapshot on connect.
        data = await self._build_dashboard_data(user)
        await self._send_json({"type": "dashboard.update", "data": data})

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.GROUP_NAME, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        """Handle client messages – currently only manual refresh requests."""
        if text_data:
            try:
                content = json.loads(text_data)
            except (json.JSONDecodeError, TypeError):
                return
            if content.get("type") == "refresh":
                user = self.scope.get("user")
                if user and not user.is_anonymous:
                    data = await self._build_dashboard_data(user)
                    await self._send_json({"type": "dashboard.update", "data": data})

    # ── Group message handler ────────────────────────────────
    async def dashboard_refresh(self, event):
        """Called when *any* worker broadcasts a refresh to the group."""
        user = self.scope.get("user")
        if user and not user.is_anonymous:
            data = await self._build_dashboard_data(user)
            await self._send_json({"type": "dashboard.update", "data": data})

    async def _send_json(self, content):
        """Send a JSON-serialised message to the client."""
        await self.send(text_data=json.dumps(content))

    # ── Data builder ─────────────────────────────────────────
    @database_sync_to_async
    def _build_dashboard_data(self, user):  # noqa: C901
        """Return a JSON-serialisable dict mirroring GeneralDashboardView context."""
        from assets.models import (
            AssetDependency,
            AssetGroup,
            EssentialAsset,
            Supplier,
            SupplierDependency,
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
        from context.models import (
            Activity,
            Issue,
            Objective,
            Role,
            Scope,
            Site,
            Stakeholder,
            SwotAnalysis,
        )
        from risks.models import (
            Risk,
            RiskAcceptance,
            RiskAssessment,
            RiskTreatmentPlan,
            Threat,
            Vulnerability,
        )

        today = timezone.now().date()

        def scope_ids():
            if user.is_superuser:
                return None
            return user.get_allowed_scope_ids()

        def filter_scoped(qs):
            ids = scope_ids()
            if ids is None:
                return qs
            model = qs.model
            if any(f.name == "scopes" for f in model._meta.many_to_many):
                return qs.filter(scopes__id__in=ids).distinct()
            return qs

        def filter_scopes(qs):
            ids = scope_ids()
            if ids is None:
                return qs
            return qs.filter(id__in=ids)

        # ── Governance ───────────────────────────────────
        scopes = filter_scopes(Scope.objects.all())
        scope_count = scopes.count()
        issue_count = filter_scoped(Issue.objects.all()).count()
        stakeholder_count = filter_scoped(Stakeholder.objects.all()).count()
        objective_count = filter_scoped(Objective.objects.all()).count()
        role_count = filter_scoped(Role.objects.all()).count()
        site_count = Site.objects.count()
        mandatory_roles_no_user = (
            filter_scoped(Role.objects.filter(is_mandatory=True))
            .annotate(user_count=Count("assigned_users"))
            .filter(user_count=0)
            .count()
        )
        swot_count = filter_scoped(SwotAnalysis.objects.all()).count()
        activity_count = filter_scoped(Activity.objects.all()).count()
        critical_activities_no_owner = filter_scoped(
            Activity.objects.filter(criticality="critical", owner__isnull=True)
        ).count()

        # ── Assets ───────────────────────────────────────
        essential_count = EssentialAsset.objects.count()
        support_count = SupportAsset.objects.count()
        dependency_count = AssetDependency.objects.count()
        spof_results = SpofDetector().detect_all()
        spof_count = spof_results["total_spof"]
        eol_count = SupportAsset.objects.filter(
            end_of_life_date__lte=today, status="active"
        ).count()
        personal_data_count = EssentialAsset.objects.filter(personal_data=True).count()
        supplier_count = Supplier.objects.count()
        expired_contract_count = Supplier.objects.filter(
            contract_end_date__lt=today, status="active"
        ).count()
        supplier_dep_count = SupplierDependency.objects.count()
        supplier_spof_count = SupplierDependency.objects.filter(
            is_single_point_of_failure=True
        ).count()
        supplier_type_count = SupplierType.objects.count()
        group_count = AssetGroup.objects.count()

        # ── Risk management ──────────────────────────────
        risk_assessment_count = filter_scoped(RiskAssessment.objects.all()).count()
        risk_count = Risk.objects.count()
        treatment_plan_count = RiskTreatmentPlan.objects.count()
        treatment_in_progress_count = RiskTreatmentPlan.objects.filter(
            status="in_progress"
        ).count()
        critical_risk_count = Risk.objects.filter(priority="critical").count()
        acceptance_count = RiskAcceptance.objects.filter(status="active").count()
        expiring_acceptance_count = RiskAcceptance.objects.filter(
            status="active",
            valid_until__lte=today + timedelta(days=30),
            valid_until__gte=today,
        ).count()
        threat_count = Threat.objects.count()
        vulnerability_count = Vulnerability.objects.count()

        # ── Compliance ───────────────────────────────────
        framework_count = filter_scoped(Framework.objects.all()).count()
        agg = filter_scoped(Framework.objects.filter(status="active")).aggregate(
            avg=Avg("compliance_level")
        )
        overall_compliance = round(agg["avg"] or 0)
        requirement_count = Requirement.objects.count()
        non_compliant_count = Requirement.objects.filter(
            compliance_status="non_compliant"
        ).count()
        assessment_count = filter_scoped(ComplianceAssessment.objects.all()).count()
        action_plan_count = filter_scoped(ComplianceActionPlan.objects.all()).count()
        overdue_plan_count = filter_scoped(
            ComplianceActionPlan.objects.filter(target_date__lt=today).exclude(
                status__in=["completed", "cancelled"]
            )
        ).count()
        mapping_count = RequirementMapping.objects.count()

        # ── Alerts ───────────────────────────────────────
        alert_count = sum(
            1
            for v in [
                mandatory_roles_no_user,
                eol_count,
                non_compliant_count,
                overdue_plan_count,
                critical_risk_count,
                expired_contract_count,
                expiring_acceptance_count,
                critical_activities_no_owner,
            ]
            if v
        )

        return {
            # Governance
            "scope_count": scope_count,
            "issue_count": issue_count,
            "stakeholder_count": stakeholder_count,
            "objective_count": objective_count,
            "role_count": role_count,
            "site_count": site_count,
            "mandatory_roles_no_user": mandatory_roles_no_user,
            "swot_count": swot_count,
            "activity_count": activity_count,
            "critical_activities_no_owner": critical_activities_no_owner,
            # Assets
            "essential_count": essential_count,
            "support_count": support_count,
            "dependency_count": dependency_count,
            "spof_count": spof_count,
            "eol_count": eol_count,
            "personal_data_count": personal_data_count,
            "supplier_count": supplier_count,
            "expired_contract_count": expired_contract_count,
            "supplier_dep_count": supplier_dep_count,
            "supplier_spof_count": supplier_spof_count,
            "supplier_type_count": supplier_type_count,
            "group_count": group_count,
            # Risk management
            "risk_assessment_count": risk_assessment_count,
            "risk_count": risk_count,
            "treatment_plan_count": treatment_plan_count,
            "treatment_in_progress_count": treatment_in_progress_count,
            "critical_risk_count": critical_risk_count,
            "acceptance_count": acceptance_count,
            "expiring_acceptance_count": expiring_acceptance_count,
            "threat_count": threat_count,
            "vulnerability_count": vulnerability_count,
            # Compliance
            "framework_count": framework_count,
            "overall_compliance": overall_compliance,
            "requirement_count": requirement_count,
            "non_compliant_count": non_compliant_count,
            "assessment_count": assessment_count,
            "action_plan_count": action_plan_count,
            "overdue_plan_count": overdue_plan_count,
            "mapping_count": mapping_count,
            # Alerts
            "alert_count": alert_count,
        }
