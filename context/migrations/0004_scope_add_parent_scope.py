import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("context", "0003_add_version_remove_scope_version"),
    ]

    operations = [
        migrations.AddField(
            model_name="scope",
            name="parent_scope",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="children",
                to="context.scope",
                verbose_name="Périmètre parent",
            ),
        ),
        migrations.AddField(
            model_name="historicalscope",
            name="parent_scope",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="context.scope",
                verbose_name="Périmètre parent",
            ),
        ),
    ]
