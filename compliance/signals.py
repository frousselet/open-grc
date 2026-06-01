"""Compliance signals.

These handlers keep the aggregated compliance levels on Section and Framework
in sync with the underlying Requirement state. Without them, the levels only
refreshed when a ComplianceAssessment was validated, which matched what the QA
report flagged as CAIRN-REQ-03 (RC-01 / RC-02 only triggered on validation).
"""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver


def _recalculate_chain(requirement):
    """Walk up the section tree from a requirement and refresh every level.

    Section.recalculate_compliance cascades down to its children, so refreshing
    the root recomputes the whole branch. Framework.recalculate_compliance is
    called afterwards to refresh the overall framework level (RC-01).
    """
    section = getattr(requirement, "section", None)
    if section is not None:
        root = section
        while root.parent_section_id:
            root = root.parent_section
        try:
            root.recalculate_compliance()
        except Exception:
            # Never let aggregation failures bubble up from a save signal.
            pass

    framework = getattr(requirement, "framework", None)
    if framework is not None:
        try:
            framework.recalculate_compliance()
        except Exception:
            pass


@receiver(post_save, sender="compliance.Requirement")
def requirement_post_save(sender, instance, created, **kwargs):
    _recalculate_chain(instance)


@receiver(post_delete, sender="compliance.Requirement")
def requirement_post_delete(sender, instance, **kwargs):
    _recalculate_chain(instance)
