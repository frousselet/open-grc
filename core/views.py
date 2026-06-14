import base64
import uuid as uuid_mod
from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Avg, Count, Max, Prefetch, Q, Subquery, OuterRef
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _, gettext_lazy, pgettext
from django.views import View
from django.views.generic import TemplateView

from core.changelog import get_changelog_between
from accounts.models import CompanySettings
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
from risks.views import (
    build_default_risk_matrix,
    build_risk_matrix,
    build_risk_treatment_flow,
)


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

        # Company identity shown in the dashboard header. Read-only access:
        # objects.first() instead of CompanySettings.get() to avoid creating
        # the singleton row on a GET request.
        ctx["company"] = CompanySettings.objects.first()

        # ── Gouvernance ──────────────────────────────────
        scopes = self._filter_scopes(Scope.objects.all())
        ctx["scope_count"] = scopes.count()
        ctx["active_scopes"] = scopes.filter(workflow_state="validated").select_related("parent_scope")[:5]
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
            criteria = RiskCriteria.objects.filter(workflow_state="validated").first()
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

        # Risk treatment flow (current level -> residual level), rendered as a
        # Sankey diagram above the matrices.
        ctx["risk_treatment_flow"] = build_risk_treatment_flow(all_risks, criteria)

        # ── Conformité ───────────────────────────────────
        # Per-framework compliance segments and the overall average come
        # from compliance.services (shared with the WebSocket refresh and
        # the predefined indicators).
        from compliance.services import (
            active_frameworks_for_scoring,
            annotate_compliance_segments,
        )

        frameworks = self._filter_scoped(Framework.objects.all())
        ctx["framework_count"] = frameworks.count()
        active_frameworks = annotate_compliance_segments(list(
            active_frameworks_for_scoring(self._filter_scoped(
                Framework.objects.all()
            )).select_related("owner").prefetch_related(
                Prefetch("scopes", queryset=Scope.objects.select_related("parent_scope")),
            )[:10]
        ))

        ctx["active_frameworks"] = active_frameworks
        # Caption of the overall-compliance card: count the requirements that
        # actually feed the average (applicable, on the frameworks above).
        ctx["tracked_requirement_count"] = sum(
            fw.req_count or 0 for fw in active_frameworks
        )

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
            ).exclude(status__in=["closed", "cancelled"])
        ).count()
        ctx["mapping_count"] = RequirementMapping.objects.count()

        # ── Today's actions ───────────────────────────
        # Presented as a prioritized to-do list rather than alarms: each
        # entry carries an action verb, a count and a link to the page
        # where the user can act on it.
        def _action(count, label, url_name, icon):
            return {
                "count": count,
                "label": label % {"count": count},
                "url": reverse(url_name),
                "icon": icon,
            }

        priority_items = []
        if ctx["critical_risk_count"]:
            priority_items.append(_action(
                ctx["critical_risk_count"],
                _("Treat %(count)d critical risk(s)"),
                "risks:risk-list", "bi-fire",
            ))
        if ctx["non_compliant_count"]:
            priority_items.append(_action(
                ctx["non_compliant_count"],
                _("Bring %(count)d requirement(s) back into compliance"),
                "compliance:requirement-list", "bi-clipboard-x",
            ))
        if ctx["overdue_plan_count"]:
            priority_items.append(_action(
                ctx["overdue_plan_count"],
                _("Reschedule %(count)d overdue action plan(s)"),
                "compliance:action-plan-list", "bi-calendar-x",
            ))

        plan_items = []
        if ctx["mandatory_roles_no_user"]:
            plan_items.append(_action(
                ctx["mandatory_roles_no_user"],
                _("Assign %(count)d mandatory role(s) without user"),
                "context:role-list", "bi-person-plus",
            ))
        if ctx["critical_activities_no_owner"]:
            plan_items.append(_action(
                ctx["critical_activities_no_owner"],
                _("Name an owner for %(count)d critical activity(ies)"),
                "context:activity-list", "bi-person-exclamation",
            ))
        if ctx["eol_count"]:
            plan_items.append(_action(
                ctx["eol_count"],
                _("Plan the replacement of %(count)d asset(s) past end of life"),
                "assets:support-asset-list", "bi-cpu",
            ))
        if ctx["expired_contract_count"]:
            plan_items.append(_action(
                ctx["expired_contract_count"],
                _("Renew %(count)d expired supplier contract(s)"),
                "assets:supplier-list", "bi-file-earmark-text",
            ))
        # Single points of failure, one entry per dependency type
        # (replaces the standalone SPOF banner)
        spof_targets = [
            ("asset", _("Mitigate %(count)d SPOF in asset dependencies"),
             "assets:dependency-list", "bi-share"),
            ("supplier", _("Mitigate %(count)d SPOF in supplier dependencies"),
             "assets:supplier-dependency-list", "bi-truck"),
            ("site_asset", _("Mitigate %(count)d SPOF in site-asset dependencies"),
             "assets:site-asset-dependency-list", "bi-building"),
            ("site_supplier", _("Mitigate %(count)d SPOF in site-supplier dependencies"),
             "assets:site-supplier-dependency-list", "bi-buildings"),
        ]
        for key, label, url_name, icon in spof_targets:
            if ctx["spof_detail"][key]:
                plan_items.append(_action(
                    ctx["spof_detail"][key], label, url_name, icon,
                ))

        watch_items = []
        if ctx["expiring_acceptance_count"]:
            watch_items.append(_action(
                ctx["expiring_acceptance_count"],
                _("Review %(count)d risk acceptance(s) expiring within 30 days"),
                "risks:acceptance-list", "bi-hourglass-split",
            ))

        action_groups = [
            {"key": "priority", "title": pgettext("today actions group", "Priority"), "tone": "high", "items": priority_items},
            {"key": "plan", "title": _("To plan"), "tone": "medium", "items": plan_items},
            {"key": "watch", "title": _("To watch"), "tone": "low", "items": watch_items},
        ]
        ctx["today_action_groups"] = [g for g in action_groups if g["items"]]

        # ── Deadlines & events (rendered inside Today's actions) ──
        calendar_items = build_upcoming_deadlines(self.request.user, today)
        ctx["calendar_items"] = calendar_items
        overdue_event_count = sum(1 for e in calendar_items if e["overdue"])

        ctx["today_action_count"] = sum(
            item["count"] for g in action_groups for item in g["items"]
        ) + overdue_event_count

        # ── Changelog popup ──────────────────────────────
        user = self.request.user
        app_version = settings.APP_VERSION
        if app_version and app_version != "dev" and user.last_seen_version != app_version:
            changelog_entries = get_changelog_between(user.last_seen_version, app_version)
            if changelog_entries:
                ctx["changelog_entries"] = changelog_entries
                ctx["changelog_new_version"] = app_version

        return ctx


class ChangelogDismissView(LoginRequiredMixin, View):
    """Mark the current app version as seen by the user (dismiss changelog popup)."""

    def post(self, request, *args, **kwargs):
        version = settings.APP_VERSION
        if version and version != "dev":
            request.user.last_seen_version = version
            request.user.save(update_fields=["last_seen_version"])
        return JsonResponse({"ok": True})


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


# ── Shared calendar event fetcher ────────────────────────────


def _safe_reverse(url_name, pk):
    try:
        return reverse(url_name, kwargs={"pk": pk})
    except Exception:
        return ""


def _filter_scoped(qs, user):
    if user.is_superuser:
        return qs
    scope_ids = user.get_allowed_scope_ids()
    if scope_ids is None:
        return qs
    model = qs.model
    if any(f.name == "scopes" for f in model._meta.many_to_many):
        return qs.filter(scopes__id__in=scope_ids).distinct()
    return qs


ALL_CATEGORIES = [
    "risk_assessment", "compliance_assessment", "action_plan",
    "treatment_plan", "scope", "objective", "framework", "swot",
    "acceptance", "supplier_review",
]


def get_calendar_events(user, start=None, end=None, categories=None):
    """Fetch calendar events for *user*. Returns list of event dicts."""
    from core.workflow import reportable

    events = []
    if not categories:
        categories = ALL_CATEGORIES

    # `deadline=True` marks dates that represent something due (reviews,
    # target dates, expiries) as opposed to informational dates (effective
    # dates, analysis dates): the dashboard uses it to surface overdue items.
    # `done` is a per-object predicate flagging items already concluded
    # (closed / completed / cancelled): their dates stay on the calendar
    # but are no longer actionable.
    # `kind` (and `kind_start` / `kind_end` for ranges) names the nature of
    # the date (review, expiry, effective date, target date...) so consumers
    # can say what the event is instead of just when it falls.
    def add(queryset, date_field, category, color, url_name, label_prefix="", deadline=False, done=None, kind=""):
        queryset = reportable(queryset)
        filters = {f"{date_field}__isnull": False}
        if start:
            filters[f"{date_field}__gte"] = start
        if end:
            filters[f"{date_field}__lte"] = end
        for obj in queryset.filter(**filters):
            plain_title = str(obj)
            title = f"{label_prefix}{plain_title}" if label_prefix else plain_title
            events.append({
                "title": title,
                "plain_title": plain_title,
                "start": getattr(obj, date_field).isoformat(),
                "color": color,
                "category": category,
                "url": _safe_reverse(url_name, obj.pk),
                "is_deadline": deadline,
                "is_done": bool(done and done(obj)),
                "kind": kind,
            })

    def add_range(queryset, sf, ef, category, color, url_name, deadline=False, done=None, kind_start="", kind_end=""):
        queryset = reportable(queryset)
        qs = queryset.filter(
            Q(**{f"{sf}__isnull": False}) | Q(**{f"{ef}__isnull": False})
        )
        if start:
            qs = qs.filter(
                Q(**{f"{ef}__gte": start})
                | Q(**{f"{ef}__isnull": True, f"{sf}__gte": start})
            )
        if end:
            qs = qs.filter(
                Q(**{f"{sf}__lte": end})
                | Q(**{f"{sf}__isnull": True, f"{ef}__lte": end})
            )
        for obj in qs:
            s = getattr(obj, sf)
            e = getattr(obj, ef)
            if not s and not e:
                continue
            ev = {
                "title": str(obj),
                "plain_title": str(obj),
                "color": color,
                "category": category,
                "url": _safe_reverse(url_name, obj.pk),
                "is_deadline": deadline,
                "is_done": bool(done and done(obj)),
                "kind_start": kind_start,
                "kind_end": kind_end,
            }
            if s and e:
                ev["start"] = min(s, e).isoformat()
                if s != e:
                    ev["end"] = max(s, e).isoformat()
            else:
                ev["start"] = (s or e).isoformat()
            events.append(ev)

    if "risk_assessment" in categories:
        qs = _filter_scoped(RiskAssessment.objects.all(), user)
        add(qs, "assessment_date", "risk_assessment", "#ef4444",
            "risks:assessment-detail", kind=_("Assessment date"))
        add(qs, "next_review_date", "risk_assessment", "#fca5a5",
            "risks:assessment-detail", _("Review: "), deadline=True, kind=_("Review"))

    if "compliance_assessment" in categories:
        qs = _filter_scoped(ComplianceAssessment.objects.all(), user)
        add_range(qs, "assessment_start_date", "assessment_end_date",
                  "compliance_assessment", "#1E3A8A",
                  "compliance:assessment-detail",
                  kind_start=_("Audit start"), kind_end=_("Audit end"))

    if "action_plan" in categories:
        from compliance.constants import ActionPlanStatus

        qs = _filter_scoped(ComplianceActionPlan.objects.all(), user)
        add_range(qs, "start_date", "target_date",
                  "action_plan", "#f59e0b",
                  "compliance:action-plan-detail", deadline=True,
                  done=lambda o: o.status in (ActionPlanStatus.CLOSED, ActionPlanStatus.CANCELLED),
                  kind_start=_("Start date"), kind_end=_("Target date"))

    if "treatment_plan" in categories:
        from risks.constants import TreatmentPlanStatus

        qs = RiskTreatmentPlan.objects.all()
        add_range(qs, "start_date", "target_date",
                  "treatment_plan", "#475569",
                  "risks:treatment-plan-detail", deadline=True,
                  done=lambda o: o.status in (TreatmentPlanStatus.COMPLETED, TreatmentPlanStatus.CANCELLED),
                  kind_start=_("Start date"), kind_end=_("Target date"))

    if "scope" in categories:
        qs = Scope.objects.all()
        add(qs, "effective_date", "scope", "#06b6d4", "context:scope-detail",
            kind=_("Effective date"))
        add(qs, "review_date", "scope", "#67e8f9",
            "context:scope-detail", _("Review: "), deadline=True, kind=_("Review"))

    if "objective" in categories:
        from context.constants import ObjectiveStatus

        def objective_done(o):
            return o.status in (
                ObjectiveStatus.ACHIEVED,
                ObjectiveStatus.NOT_ACHIEVED,
                ObjectiveStatus.CANCELLED,
            )

        qs = _filter_scoped(Objective.objects.all(), user)
        add(qs, "target_date", "objective", "#14b8a6",
            "context:objective-detail", deadline=True, done=objective_done,
            kind=_("Target date"))
        add(qs, "review_date", "objective", "#5eead4",
            "context:objective-detail", _("Review: "), deadline=True, done=objective_done,
            kind=_("Review"))

    if "framework" in categories:
        qs = _filter_scoped(Framework.objects.all(), user)
        add(qs, "effective_date", "framework", "#3b82f6",
            "compliance:framework-detail", kind=_("Effective date"))
        add(qs, "expiry_date", "framework", "#93c5fd",
            "compliance:framework-detail", _("Expiry: "), deadline=True, kind=_("Expiry"))
        add(qs, "review_date", "framework", "#bfdbfe",
            "compliance:framework-detail", _("Review: "), deadline=True, kind=_("Review"))

    if "swot" in categories:
        qs = _filter_scoped(SwotAnalysis.objects.all(), user)
        add(qs, "analysis_date", "swot", "#ec4899", "context:swot-detail",
            kind=_("Analysis date"))
        add(qs, "review_date", "swot", "#f9a8d4",
            "context:swot-detail", _("Review: "), deadline=True, kind=_("Review"))

    if "acceptance" in categories:
        from risks.constants import AcceptanceStatus

        def acceptance_done(o):
            return o.status in (AcceptanceStatus.REVOKED, AcceptanceStatus.RENEWED)

        qs = RiskAcceptance.objects.all()
        add(qs, "valid_until", "acceptance", "#f97316",
            "risks:acceptance-detail", deadline=True, done=acceptance_done,
            kind=_("Valid until"))
        add(qs, "review_date", "acceptance", "#fdba74",
            "risks:acceptance-detail", _("Review: "), deadline=True, done=acceptance_done,
            kind=_("Review"))

    if "supplier_review" in categories:
        filters = {"review_date__isnull": False}
        if start:
            filters["review_date__gte"] = start
        if end:
            filters["review_date__lte"] = end
        qs = SupplierRequirementReview.objects.select_related(
            "supplier_requirement__supplier"
        ).filter(**filters)
        for review in qs:
            supplier_name = review.supplier_requirement.supplier.name
            title = f"{supplier_name} : {review.supplier_requirement.title}"
            events.append({
                "title": title,
                "plain_title": title,
                "start": review.review_date.isoformat(),
                "color": "#d946ef",
                "category": "supplier_review",
                "url": _safe_reverse(
                    "assets:supplier-requirement-detail",
                    review.supplier_requirement.pk,
                ),
                "is_deadline": True,
                "kind": _("Review"),
            })

    return events


def build_upcoming_deadlines(user, today, categories=None):
    """Upcoming dates for the next 30 days, plus overdue deadlines
    (reviews, target dates, expiries) from the last 90 days, flagged as
    overdue instead of showing a negative day count.

    Each item carries the next milestone (`due`): for ranged events the
    start date until the range has begun, then the end date (the
    deadline). Shared by the dashboard's Today's actions card and the
    calendar page's Upcoming events card so both lists agree.
    """
    category_labels = {
        "risk_assessment": _("Risk assessments"),
        "compliance_assessment": _("Compliance assessments"),
        "action_plan": _("Action plans"),
        "treatment_plan": _("Treatment plans"),
        "scope": _("Scopes"),
        "objective": _("Objectives"),
        "framework": _("Frameworks"),
        "swot": _("SWOT analyses"),
        "acceptance": _("Risk acceptances"),
        "supplier_review": _("Supplier reviews"),
    }
    raw_events = get_calendar_events(
        user,
        start=today - timedelta(days=90),
        end=today + timedelta(days=30),
        categories=categories,
    )
    items = []
    for ev in raw_events:
        # Concluded items (closed / completed / cancelled plans,
        # achieved objectives...) are no longer actionable: they stay
        # on the calendar but leave the upcoming lists.
        if ev.get("is_done"):
            continue
        start_d = date.fromisoformat(ev["start"])
        end_d = date.fromisoformat(ev["end"]) if ev.get("end") else None
        # For ranges, the next milestone is the start while it has not
        # begun, then the end (the deadline). Showing the range start
        # unconditionally yielded "in -131 days" for plans already started.
        if end_d and start_d >= today:
            due = start_d
            kind = ev.get("kind_start") or ev.get("kind")
        else:
            due = end_d or start_d
            kind = (ev.get("kind_end") if end_d else None) or ev.get("kind")
        if due > today + timedelta(days=30):
            continue
        overdue = due < today
        # Past dates only matter when something is due: informational
        # dates (effective dates, analysis dates) are dropped.
        if overdue and not ev.get("is_deadline"):
            continue
        items.append({
            # The nature of the date lives in `kind`; the title stays
            # free of the "Review: " / "Expiry: " prefixes.
            "title": ev.get("plain_title") or ev["title"],
            "url": ev.get("url"),
            "color": ev["color"],
            "category_label": category_labels.get(ev["category"], ev["category"]),
            "kind": kind,
            "due": due,
            "overdue": overdue,
            "days_left": (due - today).days,
        })
    items.sort(key=lambda e: e["due"])
    return items


class CalendarEventsView(LoginRequiredMixin, View):
    """Return calendar events as JSON."""

    def get(self, request):
        events = get_calendar_events(
            request.user,
            start=request.GET.get("start"),
            end=request.GET.get("end"),
            categories=request.GET.getlist("categories") or None,
        )
        return JsonResponse(events, safe=False)


class CalendarUpcomingView(LoginRequiredMixin, View):
    """Return the upcoming-deadlines list as JSON.

    Backs the calendar page's "Upcoming events" card. Unlike the raw
    events feed, each item carries its next milestone (`due`), the
    overdue flag and the precomputed day count, so the client never
    does date arithmetic on range starts (issue #112: "in -131 days").
    """

    def get(self, request):
        today = timezone.now().date()
        items = build_upcoming_deadlines(
            request.user,
            today,
            categories=request.GET.getlist("categories") or None,
        )
        for item in items:
            item["due"] = item["due"].isoformat()
            item["kind"] = str(item["kind"]) if item["kind"] else ""
        return JsonResponse({"items": items})


# ── iCal subscription feed ──────────────────────────────────


class ICalFeedView(View):
    """Serve an iCal (.ics) feed authenticated via HTTP Basic Auth + calendar_token."""

    def get(self, request):
        user = self._authenticate(request)
        if user is None:
            resp = HttpResponse(status=401)
            resp["WWW-Authenticate"] = 'Basic realm="Cairn Calendar"'
            return resp

        from icalendar import Calendar, Event as ICalEvent

        today = date.today()
        start_iso = (today - timedelta(days=90)).isoformat()
        end_iso = (today + timedelta(days=365)).isoformat()
        events = get_calendar_events(user, start=start_iso, end=end_iso)

        cal = Calendar()
        cal.add("prodid", "-//Cairn//Calendar//EN")
        cal.add("version", "2.0")
        cal.add("calscale", "GREGORIAN")
        cal.add("method", "PUBLISH")
        cal.add("x-wr-calname", "Cairn")

        CAT_LABELS = {
            "risk_assessment": _("Risk assessments"),
            "compliance_assessment": _("Compliance assessments"),
            "action_plan": _("Action plans"),
            "treatment_plan": _("Treatment plans"),
            "scope": _("Scopes"),
            "objective": _("Objectives"),
            "framework": _("Frameworks"),
            "swot": _("SWOT analyses"),
            "acceptance": _("Risk acceptances"),
            "supplier_review": _("Supplier reviews"),
        }

        for ev in events:
            vevent = ICalEvent()
            uid_base = f"{ev['category']}-{ev['start']}-{ev['title']}"
            vevent.add("uid", f"{uid_base}@cairn")
            vevent.add("summary", ev["title"])

            dt_start = date.fromisoformat(ev["start"])
            vevent.add("dtstart", dt_start)
            if ev.get("end"):
                # iCal DTEND for DATE values is exclusive
                dt_end = date.fromisoformat(ev["end"]) + timedelta(days=1)
                vevent.add("dtend", dt_end)
            else:
                vevent.add("dtend", dt_start + timedelta(days=1))

            if ev.get("url"):
                vevent.add("url", request.build_absolute_uri(ev["url"]))
            cat_label = CAT_LABELS.get(ev["category"], ev["category"])
            vevent.add("categories", [str(cat_label)])
            vevent.add("dtstamp", timezone.now())
            cal.add_component(vevent)

        resp = HttpResponse(cal.to_ical(), content_type="text/calendar; charset=utf-8")
        resp["Content-Disposition"] = 'attachment; filename="cairn.ics"'
        return resp

    # Tokens unused for this many days are automatically revoked
    INACTIVITY_DAYS = 30

    def _authenticate(self, request):
        from accounts.models import CalendarToken

        auth = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth.startswith("Basic "):
            return None
        try:
            decoded = base64.b64decode(auth[6:]).decode("utf-8")
            email, token = decoded.split(":", 1)
        except (ValueError, UnicodeDecodeError):
            return None
        try:
            token_uuid = uuid_mod.UUID(token)
            ct = CalendarToken.objects.select_related("user").get(
                token=token_uuid, user__email=email, user__is_active=True,
            )
            # Revoke if inactive for too long
            reference_date = ct.last_used_at or ct.created_at
            if reference_date and timezone.now() - reference_date > timedelta(days=self.INACTIVITY_DAYS):
                ct.delete()
                return None
            ua = request.META.get("HTTP_USER_AGENT", "")[:255]
            CalendarToken.objects.filter(pk=ct.pk).update(
                last_used_at=timezone.now(),
                last_user_agent=ua,
            )
            return ct.user
        except (CalendarToken.DoesNotExist, ValueError):
            return None


class CalendarSubscribeView(LoginRequiredMixin, View):
    """HTMX partial: manage calendar subscription tokens."""

    def get(self, request):
        tokens = request.user.calendar_tokens.all()
        return render(request, "calendar_subscribe.html", {"tokens": tokens})

    def post(self, request):
        from accounts.models import CalendarToken

        action = request.POST.get("action")
        if action == "create":
            name = request.POST.get("name", "").strip()
            if not name:
                name = _("Calendar subscription")
            ct = CalendarToken.objects.create(user=request.user, name=name)
            tokens = request.user.calendar_tokens.all()
            return render(request, "calendar_subscribe.html", {
                "tokens": tokens,
                "new_token": ct,
            })
        elif action == "revoke":
            token_id = request.POST.get("token_id")
            request.user.calendar_tokens.filter(pk=token_id).delete()
        tokens = request.user.calendar_tokens.all()
        return render(request, "calendar_subscribe.html", {"tokens": tokens})


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

    # Class attributes are evaluated at import time, so the labels must be
    # lazy: plain gettext would bake in whatever language is active when the
    # module loads, ignoring the request language.
    NAVIGATION_ENTRIES = [
        ("home", gettext_lazy("Dashboard"), "bi-grid", None),
        ("context:scope-list", gettext_lazy("Scopes"), "bi-bullseye", None),
        ("context:issue-list", gettext_lazy("Issues"), "bi-exclamation-diamond", None),
        ("context:objective-list", gettext_lazy("Objectives"), "bi-flag", None),
        ("context:stakeholder-list", gettext_lazy("Stakeholders"), "bi-people", None),
        ("context:role-list", gettext_lazy("Roles"), "bi-person-badge", None),
        ("assets:essential-asset-list", gettext_lazy("Essential assets"), "bi-gem", None),
        ("assets:support-asset-list", gettext_lazy("Support assets"), "bi-hdd-network", None),
        ("assets:supplier-list", gettext_lazy("Suppliers"), "bi-truck", None),
        ("compliance:framework-list", gettext_lazy("Frameworks"), "bi-journal-check", None),
        ("compliance:requirement-list", gettext_lazy("Requirements"), "bi-list-check", None),
        ("compliance:assessment-list", gettext_lazy("Compliance assessments"), "bi-clipboard-check", None),
        ("compliance:action-plan-kanban", gettext_lazy("Action plans"), "bi-card-checklist", None),
        ("risks:assessment-list", gettext_lazy("Risk assessments"), "bi-shield-exclamation", None),
        ("risks:risk-list", gettext_lazy("Risk register"), "bi-exclamation-triangle", None),
        ("risks:treatment-plan-list", gettext_lazy("Treatment plans"), "bi-bandaid", None),
        ("calendar", gettext_lazy("Calendar"), "bi-calendar3", None),
    ]

    ACTION_ENTRIES = [
        ("risks:risk-create", gettext_lazy("Create a risk"), "bi-plus-circle", "risks.risk.create"),
        ("risks:assessment-create", gettext_lazy("Create a risk assessment"), "bi-plus-circle", "risks.assessment.create"),
        ("compliance:requirement-create", gettext_lazy("Create a requirement"), "bi-plus-circle", "compliance.requirement.create"),
        ("compliance:assessment-create", gettext_lazy("Create a compliance assessment"), "bi-plus-circle", "compliance.assessment.create"),
        ("compliance:action-plan-create", gettext_lazy("Create an action plan"), "bi-plus-circle", "compliance.action_plan.create"),
        ("assets:essential-asset-create", gettext_lazy("Create an essential asset"), "bi-plus-circle", "assets.essential_asset.create"),
        ("context:objective-create", gettext_lazy("Create an objective"), "bi-plus-circle", "context.objective.create"),
        ("styleguide", gettext_lazy("Open styleguide"), "bi-palette", None),
    ]

    def _navigation_group(self):
        items = []
        for name, label, icon, _required in self.NAVIGATION_ENTRIES:
            try:
                items.append({"title": str(label), "url": reverse(name), "icon": icon})
            except Exception:
                continue
        return {"label": str(_("Navigation")), "icon": "bi-compass", "items": items} if items else None

    def _actions_group(self, user):
        items = []
        for name, label, icon, perm in self.ACTION_ENTRIES:
            if perm and not user.has_perm(perm):
                continue
            try:
                items.append({"title": str(label), "url": reverse(name), "icon": icon})
            except Exception:
                continue
        return {"label": str(_("Actions")), "icon": "bi-lightning-charge", "items": items} if items else None

    def get(self, request):
        q = request.GET.get("q", "").strip()
        if len(q) < 2:
            # Empty / short query: show navigation + actions instead of nothing.
            groups = []
            nav = self._navigation_group()
            if nav:
                groups.append(nav)
            actions = self._actions_group(request.user)
            if actions:
                groups.append(actions)
            return JsonResponse({"results": groups})

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


class StyleGuideView(LoginRequiredMixin, TemplateView):
    """Internal styleguide rendering every shared UI component in its variants.

    Used as a living visual reference and a regression checkpoint when
    components evolve. Restricted to authenticated users (the page leaks
    no business data, only design primitives).
    """

    template_name = "core/styleguide.html"

    def get_context_data(self, **kwargs):
        from core.templatetags.ui import ILLUSTRATIONS, Step

        ctx = super().get_context_data(**kwargs)
        ctx["badge_types"] = ["approval", "severity", "risk", "status"]
        ctx["kpi_variants"] = ["accent", "success", "warning", "danger", "info", "secondary"]
        ctx["illustration_names"] = sorted(ILLUSTRATIONS.keys())
        ctx["stepper_steps"] = [
            Step(value="draft", label=_("Draft"), state="done"),
            Step(value="planned", label=_("Planned"), state="done"),
            Step(value="in_progress", label=_("In progress"), state="current"),
            Step(value="under_review", label=_("Under review"), state="next"),
            Step(value="closed", label=_("Closed"), state="future"),
        ]
        ctx["stepper_cancelled"] = Step(value="cancelled", label=_("Cancelled"), state="future")

        ctx["bulk_actions"] = [
            {"label": _("Export"), "url": "#", "variant": "secondary", "icon": "download"},
            {"label": _("Approve"), "url": "#", "variant": "success", "icon": "check-lg"},
            {"label": _("Delete"), "url": "#", "variant": "danger", "icon": "trash", "confirm": _("Confirm deletion?")},
        ]
        return ctx
