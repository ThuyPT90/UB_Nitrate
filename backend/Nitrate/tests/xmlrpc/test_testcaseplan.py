# -*- coding: utf-8 -*-

import unittest

from tcms.xmlrpc.api import testcaseplan
from tests import factories as f
from tests.xmlrpc.utils import XmlrpcAPIBaseTest


class TestCasePlanGet(XmlrpcAPIBaseTest):
    @classmethod
    def setUpTestData(cls):
        cls.case = f.TestCaseFactory(summary="test caseplan")
        cls.plan = f.TestPlanFactory(name="test xmlrpc")
        cls.case_plan = f.TestCasePlanFactory(case=cls.case, plan=cls.plan)

    def test_get(self):
        tcp = testcaseplan.get(None, self.case.pk, self.plan.pk)
        self.assertEqual(tcp["plan_id"], self.plan.pk)
        self.assertEqual(tcp["plan"], self.plan.name)
        self.assertEqual(tcp["case_id"], self.case.pk)
        self.assertEqual(tcp["case"], self.case.summary)

    @unittest.skip("TODO: fix get to make this test pass.")
    def test_get_with_no_args(self):
        bad_args = (None, [], (), {})
        for arg in bad_args:
            self.assertXmlrpcFaultBadRequest(testcaseplan.get, None, arg, self.plan.pk)
            self.assertXmlrpcFaultBadRequest(testcaseplan.get, None, self.case.pk, arg)

    def test_get_with_no_exist_case(self):
        self.assertXmlrpcFaultNotFound(testcaseplan.get, None, 10000, self.plan.pk)

    def test_get_with_no_exist_plan(self):
        self.assertXmlrpcFaultNotFound(testcaseplan.get, None, self.case.pk, 10000)

    @unittest.skip("TODO: fix get to make this test pass.")
    def test_get_with_non_integer_case_id(self):
        bad_args = ("A", "1", "", True, False, self, (1,))
        for arg in bad_args:
            self.assertXmlrpcFaultBadRequest(testcaseplan.get, None, arg, self.plan.pk)

    @unittest.skip("TODO: fix get to make this test pass.")
    def test_get_with_non_integer_plan_id(self):
        bad_args = ("A", "1", "", True, False, self, (1,))
        for arg in bad_args:
            self.assertXmlrpcFaultBadRequest(testcaseplan.get, None, self.case.pk, arg)

    def test_get_with_negative_plan_id(self):
        self.assertXmlrpcFaultNotFound(testcaseplan.get, None, self.case.pk, -1)

    def test_get_with_negative_case_id(self):
        self.assertXmlrpcFaultNotFound(testcaseplan.get, None, -1, self.plan.pk)


class TestCasePlanUpdate(XmlrpcAPIBaseTest):
    @classmethod
    def setUpTestData(cls):
        cls.case = f.TestCaseFactory(summary="test caseplan")
        cls.plan = f.TestPlanFactory(name="test xmlrpc")
        cls.case_plan = f.TestCasePlanFactory(case=cls.case, plan=cls.plan)

    def test_update(self):
        tcp = testcaseplan.update(None, self.case.pk, self.plan.pk, 110)
        self.assertIsNotNone(tcp)
        self.assertEqual(tcp["sortkey"], 110)

    @unittest.skip("TODO: fix update to make this test pass.")
    def test_update_with_no_args(self):
        bad_args = (None, [], (), {})
        for arg in bad_args:
            self.assertXmlrpcFaultBadRequest(testcaseplan.update, None, arg, self.plan.pk, 100)
            self.assertXmlrpcFaultBadRequest(testcaseplan.update, None, self.case.pk, arg, 100)
            self.assertXmlrpcFaultBadRequest(
                testcaseplan.update, None, self.case.pk, self.plan.pk, arg
            )

    def test_update_with_no_exist_case(self):
        self.assertXmlrpcFaultNotFound(testcaseplan.update, None, 10000, self.plan.pk, 100)

    def test_update_with_no_exist_plan(self):
        self.assertXmlrpcFaultNotFound(testcaseplan.update, None, self.case.pk, 10000, 100)

    @unittest.skip("TODO: fix update to make this test pass.")
    def test_update_with_non_integer_case_id(self):
        bad_args = ("A", "1", "", True, False, self, (1,))
        for arg in bad_args:
            self.assertXmlrpcFaultBadRequest(testcaseplan.update, None, arg, self.plan.pk, 100)

    @unittest.skip("TODO: fix update to make this test pass.")
    def test_update_with_non_integer_plan_id(self):
        bad_args = ("A", "1", "", True, False, self, (1,))
        for arg in bad_args:
            self.assertXmlrpcFaultBadRequest(testcaseplan.update, None, self.case.pk, arg, 100)

    def test_update_with_negative_plan_id(self):
        self.assertXmlrpcFaultNotFound(testcaseplan.update, None, self.case.pk, -1, 100)

    def test_update_with_negative_case_id(self):
        self.assertXmlrpcFaultNotFound(testcaseplan.update, None, -1, self.plan.pk, 100)

    def test_update_with_non_integer_sortkey(self):
        original_sortkey = self.case_plan.sortkey
        testcaseplan.update(None, self.case.pk, self.plan.pk, "A")
        self.assertEqual(original_sortkey, self.case_plan.sortkey)
