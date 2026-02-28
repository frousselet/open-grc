"""Create default RiskCriteria with 5×5 ISO 27005 scales."""

from django.db import migrations


def create_default_criteria(apps, schema_editor):
    RiskCriteria = apps.get_model("risks", "RiskCriteria")
    ScaleLevel = apps.get_model("risks", "ScaleLevel")
    RiskLevel = apps.get_model("risks", "RiskLevel")
    Scope = apps.get_model("context", "Scope")

    # Don't overwrite if a default already exists
    if RiskCriteria.objects.filter(is_default=True).exists():
        return

    # scope is required (ScopedModel) — use first available scope
    scope = Scope.objects.order_by("created_at").first()
    if not scope:
        return

    # Symmetric risk_matrix JSON: "likelihood,impact" → risk_level
    # Uses score = L + I - 1, mapped to 5 risk levels
    risk_matrix = {
        "5,1": 3, "5,2": 4, "5,3": 4, "5,4": 5, "5,5": 5,
        "4,1": 3, "4,2": 3, "4,3": 4, "4,4": 4, "4,5": 5,
        "3,1": 2, "3,2": 3, "3,3": 3, "3,4": 4, "3,5": 4,
        "2,1": 2, "2,2": 2, "2,3": 3, "2,4": 3, "2,5": 4,
        "1,1": 1, "1,2": 2, "1,3": 2, "1,4": 3, "1,5": 3,
    }

    criteria = RiskCriteria.objects.create(
        scope=scope,
        name="Matrice par défaut (ISO 27005)",
        description="Matrice de risques 5×5 standard ISO 27005.",
        risk_matrix=risk_matrix,
        acceptance_threshold=2,
        is_default=True,
        status="active",
    )

    # Likelihood scale
    for level, name in [
        (1, "Très improbable"),
        (2, "Improbable"),
        (3, "Possible"),
        (4, "Probable"),
        (5, "Très probable"),
    ]:
        ScaleLevel.objects.create(
            criteria=criteria,
            scale_type="likelihood",
            level=level,
            name=name,
        )

    # Impact scale
    for level, name in [
        (1, "Négligeable"),
        (2, "Mineur"),
        (3, "Modéré"),
        (4, "Significatif"),
        (5, "Sévère"),
    ]:
        ScaleLevel.objects.create(
            criteria=criteria,
            scale_type="impact",
            level=level,
            name=name,
        )

    # Risk levels
    for level, name, color, requires_treatment in [
        (1, "Faible", "#4caf50", False),
        (2, "Modéré-Faible", "#8bc34a", False),
        (3, "Modéré", "#ffc107", True),
        (4, "Modéré-Élevé", "#ff9800", True),
        (5, "Élevé", "#e53935", True),
    ]:
        RiskLevel.objects.create(
            criteria=criteria,
            level=level,
            name=name,
            color=color,
            requires_treatment=requires_treatment,
        )


def remove_default_criteria(apps, schema_editor):
    RiskCriteria = apps.get_model("risks", "RiskCriteria")
    RiskCriteria.objects.filter(
        name="Matrice par défaut (ISO 27005)", is_default=True
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("context", "0001_initial"),
        ("risks", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_default_criteria, remove_default_criteria),
    ]
