# -*- coding: utf-8 -*-
# Generated by Django 1.11.11 on 2018-04-09 14:19
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("management", "0003_TestBuild_is_active_use_custom_bool_field"),
        ("testcases", "0005_allow_null_to_testcaseattachment_case_run"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="testcasecomponent",
            unique_together={("case", "component")},
        ),
    ]
