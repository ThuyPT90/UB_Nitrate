# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2017-12-10 11:35
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("testplans", "0002_add_initial_data"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="testplanpermission",
            unique_together=set(),
        ),
        migrations.RemoveField(
            model_name="testplanpermission",
            name="plan",
        ),
        migrations.DeleteModel(
            name="TestPlanPermission",
        ),
    ]
