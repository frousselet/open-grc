"""Convert ComplianceAssessment.framework FK to frameworks M2M."""

from django.db import migrations, models


def copy_fk_to_m2m(apps, schema_editor):
    """Copy existing framework FK values into the new M2M relationship."""
    ComplianceAssessment = apps.get_model("compliance", "ComplianceAssessment")
    for assessment in ComplianceAssessment.objects.filter(framework__isnull=False):
        assessment.frameworks.add(assessment.framework)


def copy_m2m_to_fk(apps, schema_editor):
    """Reverse: copy first M2M framework back to FK."""
    ComplianceAssessment = apps.get_model("compliance", "ComplianceAssessment")
    for assessment in ComplianceAssessment.objects.all():
        first_fw = assessment.frameworks.first()
        if first_fw:
            assessment.framework = first_fw
            assessment.save(update_fields=["framework"])


class Migration(migrations.Migration):

    dependencies = [
        ("compliance", "0022_add_not_applicable_count"),
    ]

    operations = [
        # 1. Add the M2M field (alongside existing FK)
        migrations.AddField(
            model_name="complianceassessment",
            name="frameworks",
            field=models.ManyToManyField(
                blank=True,
                related_name="assessments_new",
                to="compliance.framework",
                verbose_name="Frameworks",
            ),
        ),
        # 2. Copy FK data to M2M
        migrations.RunPython(copy_fk_to_m2m, copy_m2m_to_fk),
        # 3. Remove the old FK
        migrations.RemoveField(
            model_name="complianceassessment",
            name="framework",
        ),
        # 4. Remove framework from historical model
        migrations.RemoveField(
            model_name="historicalcomplianceassessment",
            name="framework",
        ),
        # 5. Fix the related_name to the final value
        migrations.AlterField(
            model_name="complianceassessment",
            name="frameworks",
            field=models.ManyToManyField(
                blank=True,
                related_name="assessments",
                to="compliance.framework",
                verbose_name="Frameworks",
            ),
        ),
    ]
