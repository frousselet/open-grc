from django.db.models.signals import post_save
from django.dispatch import receiver

from risks.constants import (
    EBIOS_WORKSHOP_COUNT,
    EbiosIterationType,
    EbiosWorkshopStatus,
    Methodology,
)


def ensure_ebios_artifacts(assessment):
    """Make sure every ebios_rm scaffolding row exists for `assessment`.

    Creates one StudyFramework, one SecurityBaseline, one EbiosSummary and
    six EbiosWorkshopProgress rows (W0 to W5, strategic cycle, iteration 1).
    Idempotent: nothing happens for rows already present. Safe to call from
    views and migrations.

    This is the shared implementation behind the `post_save` signal and the
    backfill data migration that catches assessments created before later
    artifacts (e.g. EbiosSummary, added in the W5 lot) joined the signal.
    """
    if assessment.methodology != Methodology.EBIOS_RM:
        return

    from risks.models import (
        EbiosSummary,
        EbiosWorkshopProgress,
        SecurityBaseline,
        StudyFramework,
    )

    StudyFramework.objects.get_or_create(
        assessment=assessment,
        defaults={"created_by": assessment.created_by},
    )
    SecurityBaseline.objects.get_or_create(
        assessment=assessment,
        defaults={"created_by": assessment.created_by},
    )
    EbiosSummary.objects.get_or_create(
        assessment=assessment,
        defaults={"created_by": assessment.created_by},
    )
    for workshop_number in range(EBIOS_WORKSHOP_COUNT):
        EbiosWorkshopProgress.objects.get_or_create(
            assessment=assessment,
            workshop_number=workshop_number,
            iteration_type=EbiosIterationType.STRATEGIC,
            iteration_number=1,
            defaults={
                "status": EbiosWorkshopStatus.NOT_STARTED,
                "created_by": assessment.created_by,
            },
        )


@receiver(post_save, sender="risks.RiskAssessment")
def bootstrap_ebios_artifacts(sender, instance, created, **kwargs):
    """post_save hook delegating to `ensure_ebios_artifacts`."""
    ensure_ebios_artifacts(instance)
