# Add unique constraint on requirement.reference and new conditional constraints.
# Split from 0012 because PostgreSQL cannot ALTER TABLE when there are
# pending trigger events from row modifications in the same transaction.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("compliance", "0012_remove_requirement_unique_requirement_reference_per_framework_and_more"),
    ]

    operations = [
        # Add unique=True to requirement.reference
        # (all references were populated by the data migration in 0012)
        migrations.AlterField(
            model_name="requirement",
            name="reference",
            field=models.CharField(
                blank=True, max_length=50, unique=True, verbose_name="Reference"
            ),
        ),
        # Add new conditional constraints
        migrations.AddConstraint(
            model_name="requirement",
            constraint=models.UniqueConstraint(
                condition=models.Q(("requirement_number", ""), _negated=True),
                fields=("framework", "requirement_number"),
                name="unique_requirement_number_per_framework",
            ),
        ),
        migrations.AddConstraint(
            model_name="section",
            constraint=models.UniqueConstraint(
                condition=models.Q(("reference", ""), _negated=True),
                fields=("framework", "reference"),
                name="unique_section_reference_per_framework",
            ),
        ),
    ]
