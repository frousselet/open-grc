"""Revamp assessment statuses and replace date fields.

Old statuses: draft, in_progress, completed, validated, archived
New statuses: draft, planned, in_progress, completed, closed

Old fields: assessment_date, review_date, validated_by, validated_at
New fields: assessment_start_date, assessment_end_date
"""

import django.db.models.deletion
from django.db import migrations, models


def migrate_dates_and_statuses(apps, schema_editor):
    """Copy assessment_date → assessment_start_date, map old statuses to new."""
    ComplianceAssessment = apps.get_model("compliance", "ComplianceAssessment")
    for assessment in ComplianceAssessment.objects.all():
        assessment.assessment_start_date = assessment.assessment_date
        # Map old statuses to new
        status_map = {
            "draft": "draft",
            "in_progress": "in_progress",
            "completed": "completed",
            "validated": "closed",
            "archived": "closed",
        }
        assessment.status = status_map.get(assessment.status, "draft")
        assessment.save(update_fields=["assessment_start_date", "status"])


def reverse_dates_and_statuses(apps, schema_editor):
    """Copy assessment_start_date → assessment_date, map new statuses back."""
    ComplianceAssessment = apps.get_model("compliance", "ComplianceAssessment")
    for assessment in ComplianceAssessment.objects.all():
        assessment.assessment_date = (
            assessment.assessment_start_date
            or assessment.assessment_end_date
        )
        status_map = {
            "draft": "draft",
            "planned": "draft",
            "in_progress": "in_progress",
            "completed": "completed",
            "closed": "validated",
        }
        assessment.status = status_map.get(assessment.status, "draft")
        assessment.save(update_fields=["assessment_date", "status"])


class Migration(migrations.Migration):

    dependencies = [
        ("compliance", "0023_assessment_frameworks_m2m"),
    ]

    operations = [
        # 1. Add new date fields (alongside existing ones)
        migrations.AddField(
            model_name="complianceassessment",
            name="assessment_start_date",
            field=models.DateField(blank=True, null=True, verbose_name="Start date"),
        ),
        migrations.AddField(
            model_name="complianceassessment",
            name="assessment_end_date",
            field=models.DateField(blank=True, null=True, verbose_name="End date"),
        ),
        migrations.AddField(
            model_name="historicalcomplianceassessment",
            name="assessment_start_date",
            field=models.DateField(blank=True, null=True, verbose_name="Start date"),
        ),
        migrations.AddField(
            model_name="historicalcomplianceassessment",
            name="assessment_end_date",
            field=models.DateField(blank=True, null=True, verbose_name="End date"),
        ),
        # 2. Copy data and map statuses
        migrations.RunPython(
            migrate_dates_and_statuses,
            reverse_dates_and_statuses,
        ),
        # 3. Remove old fields
        migrations.RemoveField(
            model_name="complianceassessment",
            name="assessment_date",
        ),
        migrations.RemoveField(
            model_name="complianceassessment",
            name="review_date",
        ),
        migrations.RemoveField(
            model_name="complianceassessment",
            name="validated_at",
        ),
        migrations.RemoveField(
            model_name="complianceassessment",
            name="validated_by",
        ),
        migrations.RemoveField(
            model_name="historicalcomplianceassessment",
            name="assessment_date",
        ),
        migrations.RemoveField(
            model_name="historicalcomplianceassessment",
            name="review_date",
        ),
        migrations.RemoveField(
            model_name="historicalcomplianceassessment",
            name="validated_at",
        ),
        migrations.RemoveField(
            model_name="historicalcomplianceassessment",
            name="validated_by",
        ),
        # 4. Update status choices
        migrations.AlterField(
            model_name="complianceassessment",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Audit draft"),
                    ("planned", "Planned"),
                    ("in_progress", "In progress"),
                    ("completed", "Completed"),
                    ("closed", "Closed"),
                ],
                default="draft",
                max_length=20,
                verbose_name="Status",
            ),
        ),
        migrations.AlterField(
            model_name="historicalcomplianceassessment",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Audit draft"),
                    ("planned", "Planned"),
                    ("in_progress", "In progress"),
                    ("completed", "Completed"),
                    ("closed", "Closed"),
                ],
                default="draft",
                max_length=20,
                verbose_name="Status",
            ),
        ),
    ]
