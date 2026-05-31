"""Data migration: backfill EBIOS artifacts on assessments created before
later lots extended the bootstrap signal.

History:
- Lot 1 (W0+W1) added the post_save signal creating StudyFramework,
  SecurityBaseline and six EbiosWorkshopProgress rows on every ebios_rm
  assessment.
- Lot 5 (W5) extended that signal to also create one EbiosSummary.

Assessments persisted between lot 1 and lot 5 therefore have all the W0..W4
artifacts but no EbiosSummary, which breaks the W5 detail page. This
migration walks every ebios_rm assessment and creates the four
singleton-ish artifacts so every existing record is brought up to the
current schema without re-saving (which would also re-run the signal).

References are assigned explicitly because the historical models obtained
via apps.get_model bypass ReferenceGeneratorMixin.save(); the unique
constraint on `reference` would otherwise reject the second insert with an
empty value. The migration also backfills any empty references left behind
by a prior failed run, so it is safe to re-apply.

Idempotent: assessments that already carry every artifact are no-ops.
"""

from django.db import migrations


PREFIXES = {
    "StudyFramework": "EFRA",
    "SecurityBaseline": "EBSL",
    "EbiosSummary": "ESUM",
    "EbiosWorkshopProgress": "EWSP",
}


def _max_reference_num(Model, prefix):
    prefix_with_dash = f"{prefix}-"
    prefix_len = len(prefix_with_dash)
    max_num = 0
    refs = Model.objects.filter(
        reference__startswith=prefix_with_dash
    ).values_list("reference", flat=True)
    for ref in refs:
        try:
            n = int(ref[prefix_len:])
        except (ValueError, IndexError):
            continue
        if n > max_num:
            max_num = n
    return max_num


def _heal_empty_references(Model, prefix):
    """Assign a real reference to any row left with `reference=""`.

    A previous failed run of this migration may have inserted rows with an
    empty reference; the unique constraint then blocks any further insert.
    """
    next_num = _max_reference_num(Model, prefix) + 1
    empty = Model.objects.filter(reference="").order_by("created_at")
    for row in empty:
        row.reference = f"{prefix}-{next_num}"
        row.save(update_fields=["reference"])
        next_num += 1


def forwards(apps, schema_editor):
    RiskAssessment = apps.get_model("risks", "RiskAssessment")
    StudyFramework = apps.get_model("risks", "StudyFramework")
    SecurityBaseline = apps.get_model("risks", "SecurityBaseline")
    EbiosSummary = apps.get_model("risks", "EbiosSummary")
    EbiosWorkshopProgress = apps.get_model("risks", "EbiosWorkshopProgress")

    models_by_name = {
        "StudyFramework": StudyFramework,
        "SecurityBaseline": SecurityBaseline,
        "EbiosSummary": EbiosSummary,
        "EbiosWorkshopProgress": EbiosWorkshopProgress,
    }

    for name, Model in models_by_name.items():
        _heal_empty_references(Model, PREFIXES[name])

    counters = {
        prefix: _max_reference_num(models_by_name[name], prefix)
        for name, prefix in PREFIXES.items()
    }

    def next_ref(prefix):
        counters[prefix] += 1
        return f"{prefix}-{counters[prefix]}"

    def ensure_singleton(Model, prefix, assessment, extra_defaults=None):
        if Model.objects.filter(assessment=assessment).exists():
            return
        Model.objects.create(
            assessment=assessment,
            reference=next_ref(prefix),
            created_by_id=assessment.created_by_id,
            **(extra_defaults or {}),
        )

    EBIOS_WORKSHOP_COUNT = 6  # W0..W5
    ITERATION_TYPE_STRATEGIC = "strategic"
    WORKSHOP_STATUS_NOT_STARTED = "not_started"

    qs = RiskAssessment.objects.filter(methodology="ebios_rm")
    for assessment in qs.iterator(chunk_size=200):
        ensure_singleton(StudyFramework, "EFRA", assessment)
        ensure_singleton(SecurityBaseline, "EBSL", assessment)
        ensure_singleton(EbiosSummary, "ESUM", assessment)

        for workshop_number in range(EBIOS_WORKSHOP_COUNT):
            exists = EbiosWorkshopProgress.objects.filter(
                assessment=assessment,
                workshop_number=workshop_number,
                iteration_type=ITERATION_TYPE_STRATEGIC,
                iteration_number=1,
            ).exists()
            if exists:
                continue
            EbiosWorkshopProgress.objects.create(
                assessment=assessment,
                workshop_number=workshop_number,
                iteration_type=ITERATION_TYPE_STRATEGIC,
                iteration_number=1,
                status=WORKSHOP_STATUS_NOT_STARTED,
                reference=next_ref("EWSP"),
                created_by_id=assessment.created_by_id,
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
