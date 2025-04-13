# -*- coding: utf-8 -*-
from django.contrib import admin

from tcms.testruns.models import TestCaseRunStatus, TestRun


@admin.register(TestRun)
class TestRunAdmin(admin.ModelAdmin):
    # search_fields=(('run_id',))
    list_filter = ["manager", "default_tester"]
    list_display = ("run_id", "estimated_time", "plan")


@admin.register(TestCaseRunStatus)
class TestCaseRunStatusAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    list_display = ("id", "name", "description", "sortkey")


