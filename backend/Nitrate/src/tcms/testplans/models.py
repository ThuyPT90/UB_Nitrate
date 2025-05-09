# -*- coding: utf-8 -*-

from datetime import datetime
from textwrap import dedent
from typing import Any, Optional, Union

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Max, QuerySet
from django.db.models.signals import post_delete, post_save, pre_delete, pre_save
from django.dispatch import receiver
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from uuslug import slugify

from tcms.core.models import TCMSActionModel
from tcms.core.raw_sql import RawSQL
from tcms.core.tcms_router import connection
from tcms.core.utils import checksum
from tcms.management.models import TCMSEnvGroup, TestAttachment, TestTag, Version
from tcms.testcases.models import TestCase, TestCaseCategory, TestCasePlan, TestCaseStatus
from tcms.testplans import signals as plan_watchers

try:
    from tcms.plugins_support.signals import register_model
except ImportError:
    register_model = None  # type: ignore


class TestPlanType(TCMSActionModel):
    id = models.AutoField(db_column="type_id", primary_key=True)
    name = models.CharField(max_length=64, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "test_plan_types"
        ordering = ["name"]


class TestPlan(TCMSActionModel):
    """A plan within the TCMS"""

    plan_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, db_index=True)
    create_date = models.DateTimeField(db_column="creation_date", auto_now_add=True)
    is_active = models.BooleanField(db_column="isactive", default=True, db_index=True)
    extra_link = models.CharField(max_length=1024, default=None, blank=True, null=True)

    product_version = models.ForeignKey(Version, related_name="plans", on_delete=models.CASCADE)
    owner = models.ForeignKey(
        "auth.User",
        blank=True,
        null=True,
        related_name="myplans",
        on_delete=models.CASCADE,
    )
    author = models.ForeignKey("auth.User", on_delete=models.CASCADE)
    product = models.ForeignKey("management.Product", related_name="plan", on_delete=models.CASCADE)
    type = models.ForeignKey(TestPlanType, on_delete=models.CASCADE)
    parent = models.ForeignKey(
        "self",
        blank=True,
        null=True,
        related_name="child_set",
        on_delete=models.SET_NULL,
    )

    attachments = models.ManyToManyField(
        "management.TestAttachment", through="testplans.TestPlanAttachment"
    )

    component = models.ManyToManyField(
        "management.Component", through="testplans.TestPlanComponent"
    )
    env_group = models.ManyToManyField(
        "management.TCMSEnvGroup", related_name="plans", through="TCMSEnvPlanMap"
    )  # type: ignore
    tag = models.ManyToManyField("management.TestTag", through="testplans.TestPlanTag")

    class Meta:
        db_table = "test_plans"
        indexes = [models.Index(fields=["product", "plan_id"])]

    def __str__(self):
        return self.name

    @classmethod
    def to_xmlrpc(cls, query=None):
        from tcms.xmlrpc.serializer import TestPlanXMLRPCSerializer
        from tcms.xmlrpc.utils import distinct_filter

        _query = query or {}
        qs = distinct_filter(TestPlan, _query).order_by("pk")
        s = TestPlanXMLRPCSerializer(model_class=cls, queryset=qs)
        return s.serialize_queryset()

    @classmethod
    def search(cls, query: Optional[dict[str, Any]] = None) -> QuerySet:
        """Search test plans"""
        from django.db.models import Q

        new_query: dict[str, Any] = {}

        query_criteria = query or {}
        for k, v in query_criteria.items():
            if v and k not in ["action", "t", "f", "a"]:
                new_query[k] = hasattr(v, "strip") and v.strip() or v

        filter_args: list[Q] = []
        if search_keyword := new_query.get("search"):
            filter_args.append(
                Q(plan_id__icontains=search_keyword) | Q(name__icontains=search_keyword)
            )
            del new_query["search"]

        return cls.objects.filter(*filter_args, **new_query).distinct()

    @classmethod
    def apply_subtotal(
        cls,
        queryset: QuerySet,
        cases_count: bool = False,
        runs_count: bool = False,
        children_count: bool = False,
    ) -> QuerySet:
        select = {}
        if cases_count:
            select["cases_count"] = RawSQL.num_cases
        if runs_count:
            select["runs_count"] = RawSQL.num_runs
        if children_count:
            select["children_count"] = RawSQL.num_child_plans
        if select:
            queryset = queryset.extra(select=select)  # nosec
        return queryset

    def latest_text(self):
        return self.text.select_related("author").order_by("-plan_text_version").first()

    def text_exist(self) -> bool:
        return self.text.exists()

    def text_checksum(self) -> Optional[str]:
        text = self.text.order_by("-plan_text_version").only("checksum").first()
        return text.checksum if text else None

    def get_text_with_version(self, plan_text_version=None):
        if plan_text_version:
            try:
                return self.text.get(plan_text_version=plan_text_version)
            except TestPlanText.DoesNotExist:
                return None

        return self.latest_text()

    def add_text(
        self,
        author: User,
        plan_text: str,
        created_at: Optional[datetime] = None,
        plan_text_version=None,
        text_checksum=None,
    ):
        """Add text to this plan.

        :param created_at: the time when this text is added. If omitted,
            ``datetime.now`` is called to get the time.
        :type created_at: datetime or None
        """
        if plan_text is None:
            return None

        if not plan_text_version:
            latest_text = self.latest_text()
            if latest_text:
                plan_text_version = latest_text.plan_text_version + 1
            else:
                plan_text_version = 1

        if not text_checksum:
            old_checksum = self.text_checksum()
            new_checksum = checksum(plan_text)
            if old_checksum == new_checksum:
                return self.latest_text()

        text_data = {
            "plan_text_version": plan_text_version,
            "author": author,
            "plan_text": plan_text,
            "checksum": text_checksum or checksum(plan_text),
        }
        if created_at is not None:
            text_data["create_date"] = created_at
        return self.text.create(**text_data)

    def add_case(self, case: TestCase, sortkey: Union[int, None] = 1):
        """Add a case"""
        tcp, is_created = TestCasePlan.objects.get_or_create(plan=self, case=case)
        if is_created:
            tcp.sortkey = sortkey
            tcp.save(update_fields=["sortkey"])

    def add_component(self, component):
        try:
            return TestPlanComponent.objects.create(
                plan=self,
                component=component,
            )
        except Exception:
            return False

    def add_env_group(self, env_group: TCMSEnvGroup):
        # Create the env plan map
        return TCMSEnvPlanMap.objects.create(
            plan=self,
            group=env_group,
        )

    def add_attachment(self, attachment: TestAttachment):
        return TestPlanAttachment.objects.create(
            plan=self,
            attachment=attachment,
        )

    def add_tag(self, tag: TestTag):
        return TestPlanTag.objects.get_or_create(plan=self, tag=tag)

    def remove_tag(self, tag: TestTag):
        TestPlanTag.objects.filter(plan=self, tag=tag).delete()

    def remove_component(self, component):
        try:
            return TestPlanComponent.objects.get(plan=self, component=component).delete()
        except Exception:
            return False

    def clear_env_groups(self):
        # Remove old env groups because we only maintanence on group per plan.
        return TCMSEnvPlanMap.objects.filter(plan=self).delete()

    def delete_case(self, case):
        TestCasePlan.objects.filter(case=case.pk, plan=self.pk).delete()

    def get_absolute_url(self):
        return reverse(
            "plan-get",
            kwargs={
                "plan_id": self.plan_id,
                "slug": slugify(self.name),
            },
        )

    def get_case_sortkey(self) -> Optional[int]:
        """
        Get case sortkey.
        """
        result = TestCasePlan.objects.filter(plan=self).aggregate(Max("sortkey"))
        sortkey = result["sortkey__max"]
        if sortkey is None:
            return None
        else:
            return sortkey + 10

    def make_cloned_name(self):
        """Make default name of cloned plan"""
        return f"Copy of {self.name}"

    def clone(
        self,
        new_name=None,
        product=None,
        version=None,
        new_original_author=None,
        set_parent=True,
        copy_texts=True,
        default_text_author=None,
        copy_attachments=True,
        copy_environment_group=True,
        link_cases=True,
        copy_cases=None,
        new_case_author=None,
        new_case_default_tester=None,
        default_component_initial_owner=None,
    ):
        """Clone this plan

        :param str new_name: New name of cloned plan. If not passed, make_cloned_name is called
            to generate a default one.
        :param product: Product of cloned plan. If not passed, original plan's product is used.
        :param version: Product version of cloned plan. If not passed, original plan's
            product_version is used.
        :param new_original_author: New author of cloned plan. If not passed, original plan's
            author is used.
        :param bool set_parent: Whether to set original plan as parent of cloned plan.
            Set by default.
        :param bool copy_texts: Whether to copy the four text. Copy by default.
        :param default_text_author: When not copy the four text, new text will be created.
            This is the default author of new created text.
        :param bool copy_attachments: Whether to copy attachments. Copy by default.
        :param bool copy_environment_group: Whether to copy environment groups. Copy by default.
        :param bool link_cases: Whether to link cases to cloned plan. Default is True.
        :param bool copy_cases: Whether to copy cases to cloned plan instead of just linking them.
            Default is False.
        :param new_case_author: The author of copied cases. Used only if copy cases.
        :param new_case_default_tester: The default tester of copied cases. Used only if copy cases.
        :param default_component_initial_owner: Used only if copy cases. If copied case does not
            have original case' component, create it and use this value as the initial_owner.
        :rtype: cloned plan
        """

        if not copy_texts and not default_text_author:
            raise ValueError("Missing default text author when not copy texts.")

        if copy_cases and not default_component_initial_owner:
            raise ValueError("Missing default component initial owner when copy cases.")

        copied_create_date = datetime(
            self.create_date.year,
            self.create_date.month,
            self.create_date.day,
            hour=self.create_date.hour,
            minute=self.create_date.minute,
            second=self.create_date.second,
            microsecond=self.create_date.microsecond,
        )
        tp_dest = TestPlan.objects.create(
            name=new_name or self.make_cloned_name(),
            product=product or self.product,
            author=new_original_author or self.author,
            type=self.type,
            product_version=version or self.product_version,
            create_date=copied_create_date,
            is_active=self.is_active,
            extra_link=self.extra_link,
            parent=self if set_parent else None,
        )

        # Copy the plan documents
        if copy_texts:
            tptxts_src = self.text.all()
            for tptxt_src in tptxts_src:
                tp_dest.add_text(
                    plan_text_version=tptxt_src.plan_text_version,
                    author=tptxt_src.author,
                    created_at=tptxt_src.create_date,
                    plan_text=tptxt_src.plan_text,
                )
        else:
            tp_dest.add_text(author=default_text_author, plan_text="")

        # Copy the plan tags
        for tp_tag_src in self.tag.all():
            tp_dest.add_tag(tag=tp_tag_src)

        # Copy the plan attachments
        if copy_attachments:
            for tp_attach_src in self.attachments.all():
                tp_dest.add_attachment(attachment=tp_attach_src)

        # Copy the environment group
        if copy_environment_group:
            for env_group in self.env_group.all():
                tp_dest.add_env_group(env_group=env_group)

        # Link the cases of the plan
        if link_cases:
            tpcases_src = self.case.all()

            if copy_cases:
                for tpcase_src in tpcases_src:
                    tcp = get_object_or_404(TestCasePlan, plan=self, case=tpcase_src)
                    author = new_case_author or tpcase_src.author
                    default_tester = new_case_default_tester or tpcase_src.default_tester

                    tc_category, b_created = TestCaseCategory.objects.get_or_create(
                        name=tpcase_src.category.name, product=product or self.product
                    )

                    tpcase_dest = TestCase.objects.create(
                        create_date=tpcase_src.create_date,
                        is_automated=tpcase_src.is_automated,
                        script=tpcase_src.script,
                        arguments=tpcase_src.arguments,
                        summary=tpcase_src.summary,
                        requirement=tpcase_src.requirement,
                        alias=tpcase_src.alias,
                        estimated_time=tpcase_src.estimated_time,
                        case_status=TestCaseStatus.get("PROPOSED"),
                        category=tc_category,
                        priority=tpcase_src.priority,
                        author=author,
                        default_tester=default_tester,
                    )

                    # Add case to plan.
                    tp_dest.add_case(tpcase_dest, tcp.sortkey)

                    for tc_tag_src in tpcase_src.tag.all():
                        tpcase_dest.add_tag(tag=tc_tag_src)

                    for component in tpcase_src.component.filter(product__id=self.product_id):
                        try:
                            new_c = tp_dest.product.component.get(name=component.name)
                        except ObjectDoesNotExist:
                            new_c = tp_dest.product.component.create(
                                name=component.name,
                                initial_owner=default_component_initial_owner,
                                description=component.description,
                            )

                        tpcase_dest.add_component(new_c)

                    text = tpcase_src.latest_text()

                    if text:
                        tpcase_dest.add_text(
                            author=text.author,
                            action=text.action,
                            effect=text.effect,
                            setup=text.setup,
                            breakdown=text.breakdown,
                            create_date=text.create_date,
                        )
            else:
                for tpcase_src in tpcases_src:
                    tcp = get_object_or_404(TestCasePlan, plan=self, case=tpcase_src)
                    tp_dest.add_case(tpcase_src, tcp.sortkey)

        return tp_dest

    def import_cases(self, cases_info, sortkey_step=10):
        """Import a list of cases

        :param cases_info: list of mappings, each of which contains data to
            create a case. This information is created from case XML document
            which is exported previously from Nitrate.
        :type cases_info: list[dict]
        """
        sortkey = 1
        for info in cases_info:
            self._import_case(info, sortkey=sortkey)
            sortkey += sortkey_step

    def _import_case(self, case_info, sortkey):
        """Import a case

        :param dict case_info: refer to `import_cases`. This is one of the case
            information in the list.
        :param int sortkey: the sort key of imported case.
        """
        category, _ = TestCaseCategory.objects.get_or_create(
            product=self.product, name=case_info["category_name"]
        )

        tc = TestCase.objects.create(
            is_automated=case_info["is_automated"],
            script="",
            arguments="",
            summary=case_info["summary"],
            requirement="",
            alias="",
            estimated_time=0,
            case_status_id=case_info["case_status_id"],
            category_id=category.id,
            priority_id=case_info["priority_id"],
            author_id=case_info["author_id"],
            default_tester_id=case_info["default_tester_id"],
            notes=case_info["notes"],
        )

        tc.add_text(
            case_text_version=1,
            author=case_info["author"],
            action=case_info["action"],
            effect=case_info["effect"],
            setup=case_info["setup"],
            breakdown=case_info["breakdown"],
        )

        # handle tags
        if case_info["tags"]:
            for tag in case_info["tags"]:
                tc.add_tag(tag=tag)

        self.add_case(tc, sortkey=sortkey)

    def get_descendant_ids(self, direct: bool = False) -> list[int]:
        if direct:
            sql = dedent(
                """
                WITH RECURSIVE sub_tree AS (
                    SELECT plan_id, 0 as depth FROM test_plans WHERE plan_id = %s
                    UNION ALL
                    SELECT tp.plan_id, depth + 1 FROM test_plans AS tp, sub_tree AS st
                    WHERE tp.parent_id = st.plan_id
                )
                SELECT plan_id FROM sub_tree WHERE depth = 1;
            """
            )
        else:
            sql = dedent(
                """
                WITH RECURSIVE sub_tree AS (
                    SELECT plan_id, 0 as depth FROM test_plans WHERE plan_id = %s
                    UNION ALL
                    SELECT tp.plan_id, depth + 1 FROM test_plans AS tp, sub_tree AS st
                    WHERE tp.parent_id = st.plan_id
                )
                SELECT plan_id FROM sub_tree WHERE depth > 0;
            """
            )
        with connection.reader_cursor as cursor:
            cursor.execute(sql, [self.pk])
            return [row[0] for row in cursor.fetchall()]

    def get_descendants(self):
        descendant_ids = self.get_descendant_ids()
        return TestPlan.objects.filter(pk__in=descendant_ids)

    def get_ancestor_ids(self) -> list[int]:
        sql_ancestors = dedent(
            """
            WITH RECURSIVE sub_tree AS (
                SELECT plan_id, parent_id FROM test_plans
                WHERE plan_id = %s
                UNION ALL
                SELECT tp.plan_id, tp.parent_id
                FROM test_plans AS tp, sub_tree AS st
                WHERE st.parent_id = tp.plan_id
            )
            SELECT * FROM sub_tree;
        """
        )
        with connection.reader_cursor as cursor:
            cursor.execute(sql_ancestors, [self.pk])
            result = [row[0] for row in cursor.fetchall()]
            result.remove(self.pk)
            return result

    def get_ancestors(self) -> QuerySet:
        ancestor_ids = self.get_ancestor_ids()
        return TestPlan.objects.filter(pk__in=ancestor_ids)

    def get_notification_recipients(self) -> list[str]:
        recipients: set[str] = set()
        emailing = self.email_settings
        if emailing.auto_to_plan_owner and self.owner:
            recipients.add(self.owner.email)
        if emailing.auto_to_plan_author:
            recipients.add(self.author.email)
        if emailing.auto_to_case_owner:
            for email_addr in self.case.values_list("author__email", flat=True):
                if email_addr:
                    recipients.add(email_addr)
        if emailing.auto_to_case_default_tester:
            for email_addr in self.case.values_list("default_tester__email", flat=True):
                if email_addr:
                    recipients.add(email_addr)
        return [r for r in recipients if r]


class TestPlanText(TCMSActionModel):
    plan = models.ForeignKey(TestPlan, related_name="text", on_delete=models.CASCADE)
    plan_text_version = models.IntegerField()
    author = models.ForeignKey("auth.User", db_column="who", on_delete=models.CASCADE)
    create_date = models.DateTimeField(default=timezone.now, db_column="creation_ts")
    plan_text = models.TextField(blank=True)
    checksum = models.CharField(max_length=32)

    class Meta:
        db_table = "test_plan_texts"
        ordering = ["plan", "-plan_text_version"]
        unique_together = ("plan", "plan_text_version")


class TestPlanAttachment(models.Model):
    attachment = models.ForeignKey("management.TestAttachment", on_delete=models.CASCADE)
    plan = models.ForeignKey(TestPlan, on_delete=models.CASCADE)

    class Meta:
        db_table = "test_plan_attachments"


class TestPlanTag(models.Model):
    tag = models.ForeignKey("management.TestTag", on_delete=models.CASCADE)
    plan = models.ForeignKey(TestPlan, on_delete=models.CASCADE)
    user = models.IntegerField(default="1", db_column="userid")

    class Meta:
        db_table = "test_plan_tags"


class TestPlanComponent(models.Model):
    plan = models.ForeignKey(TestPlan, on_delete=models.CASCADE)
    component = models.ForeignKey("management.Component", on_delete=models.CASCADE)

    class Meta:
        db_table = "test_plan_components"
        unique_together = ("plan", "component")


class TestPlanEmailSettings(models.Model):
    plan = models.OneToOneField(TestPlan, related_name="email_settings", on_delete=models.CASCADE)
    is_active = models.BooleanField(default=False)
    auto_to_plan_owner = models.BooleanField(default=False)
    auto_to_plan_author = models.BooleanField(default=False)
    auto_to_case_owner = models.BooleanField(default=False)
    auto_to_case_default_tester = models.BooleanField(default=False)
    notify_on_plan_update = models.BooleanField(default=False)
    notify_on_plan_delete = models.BooleanField(default=False)
    notify_on_case_update = models.BooleanField(default=False)

    class Meta:
        pass


class TCMSEnvPlanMap(models.Model):
    plan = models.ForeignKey(TestPlan, on_delete=models.CASCADE)
    group = models.ForeignKey("management.TCMSEnvGroup", on_delete=models.CASCADE)

    class Meta:
        db_table = "tcms_env_plan_map"


@receiver(post_save, sender=TestPlan)
def set_email_settings_to_new_plan(sender, **kwargs):
    if kwargs["created"]:
        TestPlanEmailSettings.objects.create(plan=kwargs["instance"])


if register_model:  # type: ignore
    register_model(TestPlan)
    register_model(TestPlanText)
    register_model(TestPlanType)
    register_model(TestPlanTag)
    register_model(TestPlanComponent)


def _listen():
    post_save.connect(plan_watchers.notify_on_plan_is_updated, TestPlan)
    pre_delete.connect(plan_watchers.load_email_settings_for_later_deletion, TestPlan)
    post_delete.connect(plan_watchers.notify_deletion_of_plan, TestPlan)
    pre_save.connect(plan_watchers.pre_save_clean, TestPlan)


def _disconnect_signals():
    """used in testing"""
    post_save.disconnect(plan_watchers.notify_on_plan_is_updated, TestPlan)
    pre_delete.disconnect(plan_watchers.load_email_settings_for_later_deletion, TestPlan)
    post_delete.disconnect(plan_watchers.notify_deletion_of_plan, TestPlan)
    pre_save.disconnect(plan_watchers.pre_save_clean, TestPlan)


if settings.LISTENING_MODEL_SIGNAL:  # pragma: no cover
    _listen()
