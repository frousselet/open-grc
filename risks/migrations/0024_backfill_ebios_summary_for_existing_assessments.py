"""Data migration: backfill EBIOS artifacts on assessments created before
later lots extended the bootstrap signal.

History:
- Lot 1 (W0+W1) added the post_save signal creating StudyFramework,
  SecurityBaseline and six EbiosWorkshopProgress rows on every ebios_rm
  assessment.
- Lot 5 (W5) extended that signal to also create one EbiosSummary.

Assessments persisted between lot 1 and lot 5 therefore have all the W0..W4
artifacts but no EbiosSummary, which breaks the W5 detail page. This
migration walks every ebios_rm assessment and calls get_or_create on
the four singleton-ish artifacts so every existing record is brought up to
the current schema without re-saving (which would also re-run the signal).

Idempotent: assessments that already carry every artifact are no-ops.
"""

from django.db import migrations


def forwards(apps, schema_editor):
    RiskAssessment = apps.get_model("risks", "RiskAssessment")
    StudyFramework = apps.get_model("risks", "StudyFramework")
    SecurityBaseline = apps.get_model("risks", "SecurityBaseline")
    EbiosSummary = apps.get_model("risks", "EbiosSummary")
    EbiosWorkshopProgress = apps.get_model("risks", "EbiosWorkshopProgress")

    EBIOS_WORKSHOP_COUNT = 6  # W0..W5
    ITERATION_TYPE_STRATEGIC = "strategic"
    WORKSHOP_STATUS_NOT_STARTED = "not_started"

    qs = RiskAssessment.objects.filter(methodology="ebios_rm")
    for assessment in qs.iterator(chunk_size=200):
        StudyFramework.objects.get_or_create(
            assessment=assessment,
            defaults={"created_by_id": assessment.created_by_id},
        )
        SecurityBaseline.objects.get_or_create(
            assessment=assessment,
            defaults={"created_by_id": assessment.created_by_id},
        )
        EbiosSummary.objects.get_or_create(
            assessment=assessment,
            defaults={"created_by_id": assessment.created_by_id},
        )
        for workshop_number in range(EBIOS_WORKSHOP_COUNT):
            EbiosWorkshopProgress.objects.get_or_create(
                assessment=assessment,
                workshop_number=workshop_number,
                iteration_type=ITERATION_TYPE_STRATEGIC,
                iteration_number=1,
                defaults={
                    "status": WORKSHOP_STATUS_NOT_STARTED,
                    "created_by_id": assessment.created_by_id,
                },
            )


def reverse(apps, schema_editor):
    # No-op: deleting backfilled rows would discard user-supplied content
    # added since the backfill. The migration is one-way safe.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("risks", "0023_ebios_w5_summary_pacs"),
    ]

    operations = [
        migrations.RunPython(forwards, reverse),
    ]
