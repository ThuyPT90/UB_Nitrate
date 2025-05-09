# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-12-15 03:05
from django.db import migrations


def forwards(apps, schema_editor):
    IssueTracker = apps.get_model("issuetracker", "IssueTracker")

    bugzilla = IssueTracker.objects.get(name="Bugzilla")
    bugzilla.issues_display_url_fmt = (
        "http://bugzilla.example.com/buglist.cgi?bugidtype=include&bug_id={issue_keys}"
    )
    bugzilla.save(update_fields=["issues_display_url_fmt"])

    jira = IssueTracker.objects.get(name="JIRA")
    jira.issues_display_url_fmt = (
        "http://jira.example.com/issues/?jql=issuekey in ({issue_keys}) ORDER BY issuekey"
    )
    jira.save(update_fields=["issues_display_url_fmt"])


class Migration(migrations.Migration):

    dependencies = [
        ("issuetracker", "0016_issuetracker_issues_display_url_fmt"),
    ]

    operations = [migrations.RunPython(forwards, reverse_code=migrations.RunPython.noop)]
