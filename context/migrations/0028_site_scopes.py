# Generated manually on 2026-06-02

"""Add scopes M2M to Site (closes #30 part 2).

Site previously inherited from BaseModel; promoting it to ScopedModel
aligns it with every other domain entity and lets perimeters frame
which sites belong to which SMSI scope. The relation stays optional
(M2M, blank=True), so existing rows survive the migration unattached.

This is the schema half of the change; the conversion of
SupportAsset[type=site] rows into Site rows lives in the assets
0029 migration that follows.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("context", "0027_site_type_to_english"),
    ]

    operations = [
        migrations.AddField(
            model_name="site",
            name="scopes",
            field=models.ManyToManyField(
                blank=True,
                related_name="%(class)s_set",
                to="context.scope",
                verbose_name="Scopes",
            ),
        ),
    ]
