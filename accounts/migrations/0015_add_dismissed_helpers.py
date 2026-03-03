from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0014_add_mcp_oauth_permissions"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="dismissed_helpers",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="List of help content keys dismissed by the user.",
                verbose_name="Dismissed helpers",
            ),
        ),
    ]
