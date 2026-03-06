"""Signal handlers that broadcast dashboard refresh events via Channels.

When any domain model is created, updated, or deleted, we notify all
connected dashboard WebSocket clients so they can refresh their counters
in real time.
"""

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)

# All domain models whose changes should trigger a dashboard refresh.
_DASHBOARD_MODELS = None


def _get_dashboard_models():
    """Lazily import and return the set of models that affect the dashboard."""
    global _DASHBOARD_MODELS
    if _DASHBOARD_MODELS is not None:
        return _DASHBOARD_MODELS

    from assets.models import (
        AssetDependency,
        AssetGroup,
        EssentialAsset,
        Supplier,
        SupplierDependency,
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
    from context.models import (
        Activity,
        Indicator,
        IndicatorMeasurement,
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
        RiskCriteria,
        RiskTreatmentPlan,
        Threat,
        Vulnerability,
    )

    _DASHBOARD_MODELS = {
        # Governance
        Scope, Issue, Stakeholder, Objective, Role, Site, SwotAnalysis, Activity,
        Indicator, IndicatorMeasurement,
        # Assets
        EssentialAsset, SupportAsset, AssetDependency, AssetGroup,
        Supplier, SupplierDependency, SupplierType,
        # Risks
        RiskAssessment, Risk, RiskTreatmentPlan, RiskAcceptance,
        Threat, Vulnerability, RiskCriteria,
        # Compliance
        Framework, Requirement, ComplianceAssessment,
        ComplianceActionPlan, RequirementMapping,
    }
    return _DASHBOARD_MODELS


def _notify_dashboard():
    """Send a refresh event to the ``dashboard`` channel-layer group."""
    try:
        channel_layer = get_channel_layer()
        if channel_layer is None:
            return
        async_to_sync(channel_layer.group_send)(
            "dashboard",
            {"type": "dashboard.refresh"},
        )
    except Exception:
        logger.debug("Failed to send dashboard refresh via channel layer", exc_info=True)


@receiver(post_save)
def on_model_save(sender, instance, **kwargs):
    """Broadcast dashboard refresh when a tracked model is saved."""
    if sender in _get_dashboard_models():
        _notify_dashboard()


@receiver(post_delete)
def on_model_delete(sender, instance, **kwargs):
    """Broadcast dashboard refresh when a tracked model is deleted."""
    if sender in _get_dashboard_models():
        _notify_dashboard()
