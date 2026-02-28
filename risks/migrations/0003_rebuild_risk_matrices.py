"""Recompute all risk matrices with the symmetric formula."""

import math

from django.db import migrations


def rebuild_all_matrices(apps, schema_editor):
    RiskCriteria = apps.get_model("risks", "RiskCriteria")
    ScaleLevel = apps.get_model("risks", "ScaleLevel")
    RiskLevel = apps.get_model("risks", "RiskLevel")

    for criteria in RiskCriteria.objects.all():
        l_levels = list(
            ScaleLevel.objects.filter(criteria=criteria, scale_type="likelihood")
            .order_by("level")
            .values_list("level", flat=True)
        )
        i_levels = list(
            ScaleLevel.objects.filter(criteria=criteria, scale_type="impact")
            .order_by("level")
            .values_list("level", flat=True)
        )
        r_levels = list(
            RiskLevel.objects.filter(criteria=criteria)
            .order_by("level")
            .values_list("level", flat=True)
        )
        if not l_levels or not i_levels or not r_levels:
            continue

        max_score = max(l_levels) + max(i_levels) - 1
        num_r = len(r_levels)
        matrix = {}
        for l_val in l_levels:
            for i_val in i_levels:
                score = l_val + i_val - 1
                idx = math.ceil(score * num_r / max_score) - 1
                idx = max(0, min(idx, num_r - 1))
                matrix[f"{l_val},{i_val}"] = r_levels[idx]

        criteria.risk_matrix = matrix
        criteria.save(update_fields=["risk_matrix"])


class Migration(migrations.Migration):

    dependencies = [
        ("risks", "0002_default_risk_criteria"),
    ]

    operations = [
        migrations.RunPython(rebuild_all_matrices, migrations.RunPython.noop),
    ]
