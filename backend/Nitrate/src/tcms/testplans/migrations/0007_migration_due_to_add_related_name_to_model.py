# Generated by Django 2.2.1 on 2019-08-25 12:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("testplans", "0006_set_parent_null_when_delete_parent_plan"),
    ]

    operations = [
        migrations.AlterField(
            model_name="testplan",
            name="env_group",
            field=models.ManyToManyField(
                related_name="plans",
                through="testplans.TCMSEnvPlanMap",
                to="management.TCMSEnvGroup",
            ),
        ),
    ]
