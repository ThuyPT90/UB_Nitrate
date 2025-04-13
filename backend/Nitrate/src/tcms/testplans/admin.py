# -*- coding: utf-8 -*-
from django.contrib import admin

from tcms.testplans.models import TestPlan, TestPlanType


@admin.register(TestPlanType)
class TestPlanTypeAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    list_display = ("id", "name", "description")


@admin.register(TestPlan)
class TestPlanAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    list_filter = ["owner", "create_date"]
    list_display = ("name", "create_date", "owner", "author", "type")


