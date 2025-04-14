# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-12-15 03:02
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("issuetracker", "0015_auto_20181215_0220"),
    ]

    operations = [
        migrations.AddField(
            model_name="issuetracker",
            name="issues_display_url_fmt",
            field=models.URLField(
                default="",
                help_text="URL format to construct a display URL used to open in Web browse to display issues. For example, http://bugzilla.example.com/buglist.cgi?bug_id={issue_keys}",
            ),
            preserve_default=False,
        ),
    ]
