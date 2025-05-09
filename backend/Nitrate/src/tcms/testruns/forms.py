# -*- coding: utf-8 -*-

from django import forms
from django.contrib.auth.models import User

from tcms.core.forms import DurationField, UserField
from tcms.management.models import Product, TCMSEnvGroup, TCMSEnvValue, TestBuild, TestTag, Version
from tcms.testcases.models import TestCase
from tcms.testplans.models import TestPlan

from .models import TestCaseRun, TestCaseRunStatus, TestRun

STATUS_CHOICES = (("", "---------"), ("running", "Running"), ("finished", "Finished"))

BOOLEAN_STATUS_CHOICES = ((1, "Running"), (0, "Finished"))

PEOPLE_TYPE_CHOICES = (
    ("people", "Manager | Tester"),
    ("manager", "Manager"),
    ("default_tester", "Defaut tester"),
)

# =========== Forms for create/update ==============


class BaseRunForm(forms.Form):
    summary = forms.CharField(label="Summary", max_length=255)
    manager: forms.Field = UserField(label="Manager")
    default_tester: forms.Field = UserField(label="Default Tester", required=False)
    product = forms.ModelChoiceField(
        label="Product",
        queryset=Product.objects.all(),
        empty_label=None,
    )
    estimated_time = DurationField(required=False)
    product_version = forms.ModelChoiceField(
        label="Product Version",
        queryset=Version.objects.none(),
        empty_label=None,
    )
    build = forms.ModelChoiceField(
        label="Build",
        queryset=TestBuild.objects.none(),
        empty_label=None,
    )
    notes = forms.CharField(label="Notes", widget=forms.Textarea, required=False)
    keep_status = forms.BooleanField(
        label="Reserve Status", widget=forms.CheckboxInput(), required=False
    )
    keep_assignee = forms.BooleanField(
        label="Reserve Assignee",
        widget=forms.CheckboxInput(),
        required=False,
        initial=True,
    )
    auto_update_run_status = forms.BooleanField(
        label="Set Status Automatically",
        widget=forms.CheckboxInput(),
        help_text="Check to update test run status automatically",
        required=False,
        initial=False,
    )

    def populate(self, product_id):
        # We can dynamically set choices for a form field:
        # Seen at: http://my.opera.com/jacob7908/blog/2009/06/19/
        #          django-choicefield-queryset (Chinese)
        # Is this documented elsewhere?
        query = {"product_ids": [product_id]}
        self.fields["product_version"].queryset = Version.objects.filter(product__id=product_id)
        self.fields["build"].queryset = TestBuild.list_active(query)


class NewRunForm(BaseRunForm):
    case = forms.ModelMultipleChoiceField(
        label="Cases",
        queryset=TestCase.objects.filter(case_status__id=2).order_by("pk"),
    )


class EditRunForm(BaseRunForm):
    finished = forms.BooleanField(label="Finished", required=False)


# =========== Forms for XML-RPC functions ==============


class XMLRPCNewRunForm(BaseRunForm):
    plan = forms.ModelChoiceField(
        label="Test Plan",
        queryset=TestPlan.objects.all(),
    )
    manager = forms.ModelChoiceField(label="Manager", queryset=User.objects.all())
    default_tester = forms.ModelChoiceField(
        label="Default tester", queryset=User.objects.all(), required=False
    )
    case = forms.ModelMultipleChoiceField(
        label="Test Case",
        queryset=TestCase.objects.all(),
        required=False,
    )
    plan_text_version = forms.IntegerField(
        label="Plan text version",
        required=False,
    )
    status = forms.TypedChoiceField(coerce=int, choices=((0, 0), (1, 1)), required=False)
    tag = forms.CharField(label="Tag", required=False)

    def clean_plan_text_version(self):
        data = self.cleaned_data.get("plan_text_version")
        if not data:
            if self.cleaned_data.get("plan"):
                plan_text = self.cleaned_data["plan"].latest_text()
                data = plan_text.plan_text_version
            else:
                data = 0

        return data

    def clean_status(self):
        data = self.cleaned_data.get("status")
        if not data:
            data = 0

        return data

    def clean_tag(self):
        tag = self.cleaned_data.get("tag")
        return str(tag)


class XMLRPCUpdateRunForm(XMLRPCNewRunForm):
    plan = forms.ModelChoiceField(
        label="Test Plan",
        queryset=TestPlan.objects.all(),
        required=False,
    )
    summary = forms.CharField(label="Summary", required=False)
    manager = forms.ModelChoiceField(label="Manager", queryset=User.objects.all(), required=False)
    product = forms.ModelChoiceField(
        label="Product",
        queryset=Product.objects.all(),
        empty_label=None,
        required=False,
    )
    product_version = forms.ModelChoiceField(
        label="Product Version",
        queryset=Version.objects.none(),
        empty_label=None,
        required=False,
    )
    build = forms.ModelChoiceField(label="Build", queryset=TestBuild.objects.all(), required=False)

    def clean_status(self):
        return self.cleaned_data.get("status")


# =========== Forms for search/filter ==============


class SearchRunForm(forms.Form):
    search = forms.CharField(required=False)
    summary = forms.CharField(required=False)
    plan = forms.CharField(required=False)
    product = forms.ModelChoiceField(queryset=Product.objects.all(), required=False)
    product_version = forms.ModelChoiceField(queryset=Version.objects.none(), required=False)
    env_group = forms.ModelChoiceField(
        label="Environment Group",
        queryset=TCMSEnvGroup.get_active().all(),
        required=False,
    )
    build = forms.ModelChoiceField(
        label="Build",
        queryset=TestBuild.objects.none(),
        required=False,
    )
    people_type = forms.ChoiceField(choices=PEOPLE_TYPE_CHOICES, required=False)
    people = UserField(required=False)
    manager = UserField(required=False)
    default_tester = UserField(required=False)
    status = forms.ChoiceField(choices=STATUS_CHOICES, required=False)
    tag__name__in = forms.CharField(label="Tag", required=False)

    case_run__assignee = UserField(required=False)

    def clean_tag__name__in(self):
        return TestTag.string_to_list(self.cleaned_data["tag__name__in"])

    def populate(self, product_id=None):
        # We can dynamically set choices for a form field:
        # Seen at: http://my.opera.com/jacob7908/blog/2009/06/19/
        #          django-choicefield-queryset (Chinese)
        # Is this documented elsewhere?
        if product_id:
            self.fields["product_version"].queryset = Version.objects.filter(product__pk=product_id)
            self.fields["build"].queryset = TestBuild.objects.filter(product__pk=product_id)
        else:
            self.fields["product_version"].queryset = Version.objects.all()
            self.fields["build"].queryset = TestBuild.list_active()


# =========== Mist forms ==============


class RunCloneForm(BaseRunForm):
    build = forms.ModelChoiceField(
        label="Build",
        queryset=TestBuild.objects.none(),
        empty_label=None,
    )


class MulitpleRunsCloneForm(forms.Form):
    run = forms.ModelMultipleChoiceField(
        queryset=TestRun.objects.none(),
        widget=forms.CheckboxSelectMultiple(),
        required=False,
    )
    product = forms.ModelChoiceField(queryset=Product.objects.all(), required=False)
    product_version = forms.ModelChoiceField(queryset=Version.objects.none(), required=False)
    build = forms.ModelChoiceField(
        label="Build",
        queryset=TestBuild.objects.none(),
        empty_label=None,
    )
    manager = UserField(required=False)
    default_tester = UserField(required=False)
    # assignee = UserField(required=False)
    update_manager = forms.BooleanField(
        help_text="Unchecking will keep the original manager",
        required=False,
    )
    update_default_tester = forms.BooleanField(
        help_text="Unchecking will keep the original default tester",
        required=False,
    )
    # update_assignee = forms.BooleanField(
    # help_text='Unchecking will keep the original assignee of case runs',
    #     required=False,
    # )
    update_case_text = forms.BooleanField(
        label="Use newest case text(setup/actions/effects/breakdown)",
        help_text="Unchecking will make me the default tester of copied cases",
        required=False,
    )
    clone_cc = forms.BooleanField(help_text="Unchecking it will not clone the CC", required=False)
    clone_tag = forms.BooleanField(
        help_text="Unchecking it will not clone the tags", required=False
    )

    def populate(self, trs, product_id=None):
        self.fields["run"].queryset = TestRun.objects.filter(pk__in=trs).order_by("-pk")

        if product_id:
            self.fields["product_version"].queryset = Version.objects.filter(product__pk=product_id)
            self.fields["build"].queryset = TestBuild.objects.filter(product__pk=product_id)


class RunAndEnvValueForm(forms.Form):
    runs = forms.ModelMultipleChoiceField(
        queryset=TestRun.objects.all(),
        error_messages={
            "required": "Missing test run id to update the environment value",
            "invalid_choice": "Test run id %(value)s is not valid.",
        },
    )
    env_value = forms.ModelChoiceField(
        queryset=TCMSEnvValue.objects.all(),
        error_messages={
            "required": "Missing environment value id.",
            "invalid_choice": "Invalid environment value id.",
        },
    )


class ChangeRunEnvValueForm(forms.Form):
    runs = forms.ModelMultipleChoiceField(
        queryset=TestRun.objects.all(),
        error_messages={
            "required": "Missing test run id to update the environment value",
            "invalid_choice": "Test run id %(value)s is not valid.",
        },
    )
    old_env_value = forms.ModelChoiceField(
        queryset=TCMSEnvValue.objects.all(),
        error_messages={
            "required": "Missing old environment value id.",
            "invalid_choice": "Invalid old environment value id.",
        },
    )
    new_env_value = forms.ModelChoiceField(
        queryset=TCMSEnvValue.objects.all(),
        error_messages={
            "required": "Missing new environment value id.",
            "invalid_choice": "Invalid new environment value id.",
        },
    )


# ===========================================================================
# Case run form
# ===========================================================================


class CommentCaseRunsForm(forms.Form):
    run = forms.ModelMultipleChoiceField(
        queryset=TestCaseRun.objects.only("pk"),
        error_messages={
            "required": "No test case run id is passed to comment out.",
            "invalid_choice": "Test case run %(value)s does not exist.",
            "invalid_pk_value": "%(pk)s is not a valid test case run id.",
        },
    )
    comment = forms.CharField(error_messages={"required": "Comment is needed."})


# =========== Forms for create/update ==============


class BaseCaseRunForm(forms.Form):
    build = forms.ModelChoiceField(
        label="Build",
        queryset=TestBuild.objects.all(),
    )
    case_run_status = forms.ModelChoiceField(
        label="Case Run Status",
        queryset=TestCaseRunStatus.objects.all(),
        required=False,
    )
    assignee: forms.Field = UserField(label="Assignee", required=False)
    case_text_version = forms.IntegerField(label="Case text version", required=False)
    notes = forms.CharField(label="Notes", required=False)
    sortkey = forms.IntegerField(label="Sortkey", required=False)


class PlanFilterRunForm(forms.Form):
    build = forms.ModelChoiceField(label="Build", queryset=TestBuild.objects.all(), required=False)
    manager__username__iexact = UserField(required=False)
    plan = forms.IntegerField(required=True)
    run_id = forms.CharField(required=False)
    start_date__gt = forms.DateTimeField(required=False)
    summary__icontains = forms.CharField(required=False)
    default_tester__username__iexact = UserField(required=False)

    def __init__(self, request_data):
        super().__init__({k: v for k, v in request_data.items() if v.strip()})

    def clean(self):
        cleaned_data = {}
        for key, value in self.cleaned_data.items():
            if not value:
                continue
            if not (isinstance(value, str) and not value.strip()):
                cleaned_data[key] = value
        return cleaned_data


# =========== Forms for XML-RPC functions ==============


class XMLRPCNewCaseRunForm(BaseCaseRunForm):
    assignee = forms.ModelChoiceField(label="Assignee", queryset=User.objects.all(), required=False)
    run = forms.ModelChoiceField(
        label="Test Run",
        queryset=TestRun.objects.all(),
    )
    case = forms.ModelChoiceField(
        label="TestCase",
        queryset=TestCase.objects.all(),
    )

    def clean_case_text_version(self):
        data = self.cleaned_data.get("case_text_version")
        if not data and self.cleaned_data.get("case"):
            tc_ltxt = self.cleaned_data["case"].latest_text()
            if tc_ltxt:
                data = tc_ltxt.case_text_version

        return data

    def clean_case_run_status(self):
        data = self.cleaned_data.get("case_run_status")
        if not data:
            data = TestCaseRunStatus.get("IDLE")

        return data


class XMLRPCUpdateCaseRunForm(BaseCaseRunForm):
    assignee = forms.ModelChoiceField(label="Assignee", queryset=User.objects.all(), required=False)
    build = forms.ModelChoiceField(
        label="Build",
        queryset=TestBuild.objects.all(),
        required=False,
    )
