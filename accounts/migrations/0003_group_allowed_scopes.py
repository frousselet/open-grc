from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_populate_permissions_and_groups"),
        ("context", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="group",
            name="allowed_scopes",
            field=models.ManyToManyField(
                blank=True,
                related_name="allowed_groups",
                to="context.scope",
                verbose_name="Périmètres autorisés",
            ),
        ),
    ]
