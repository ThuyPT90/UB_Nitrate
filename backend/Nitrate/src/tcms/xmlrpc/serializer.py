# -*- coding: utf-8 -*-

import operator
from collections import OrderedDict
from datetime import datetime, timedelta
from itertools import groupby
from typing import Callable, Optional

from django.core.exceptions import ObjectDoesNotExist
from django.db.models.fields.related import ForeignKey

# TODO: to encode all strings in UTF-8 instead of mixing unicode and byte
# string.
# TODO: to claim the sequence of the primary keys of each ManyToManyField is
# arbitrary.

SECONDS_PER_MIN = 60
SECONDS_PER_HOUR = 3600  # SECONDS_PER_MIN * 60
SECONDS_PER_DAY = 86400  # SECONDS_PER_HOUR * 24


# ## Data format conversion functions ###


def do_nothing(value):
    return value


def to_str(value):
    return value if value is None else str(value)


def encode_utf8(value):
    return value if value is None else value.encode("utf-8")


def datetime_to_str(value):
    if value is None:
        return value
    return datetime.strftime(value, "%Y-%m-%d %H:%M:%S")


def timedelta_to_str(value: Optional[timedelta]):
    if value is None:
        return value
    minutes, seconds = divmod(value.seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return "%02i:%02i:%02i" % (hours, minutes, seconds)


# ## End of functions ###


class XMLRPCSerializer:
    """
    Django XMLRPC Serializer
    The goal is to process the datetime and timedelta data structure
    that python xmlrpclib can not handle.

    How to use it:
    # Model
    m = Model.objects.get(pk = 1)
    s = XMLRPCSerializer(model = m)
    s.serialize()

    Or
    # QuerySet
    q = Model.objects.all()
    s = XMLRPCSerializer(queryset = q)
    s.serialize()
    """

    def __init__(self, queryset=None, model=None):
        """Initial the class"""
        if hasattr(queryset, "__iter__"):
            self.queryset = queryset
            return
        elif hasattr(model, "__dict__"):
            self.model = model
            return

        raise TypeError("QuerySet(list) or Models(dictionary) is required")

    def serialize_model(self):
        """
        Check the fields of models and convert the data

        Returns: Dictionary
        """
        if not hasattr(self.model, "__dict__"):
            raise TypeError("Models or Dictionary is required")
        response = {}
        opts = self.model._meta
        for field in opts.local_fields:
            # for a django model, retrieving a foreignkey field
            # will fail when the field value isn't set
            try:
                value = getattr(self.model, field.name)
            except ObjectDoesNotExist:
                value = None
            if isinstance(value, datetime):
                value = datetime_to_str(value)
            if isinstance(value, timedelta):
                value = timedelta_to_str(value)
            if isinstance(field, ForeignKey):
                fk_id = "%s_id" % field.name
                if value is None:
                    response[fk_id] = None
                else:
                    response[fk_id] = getattr(self.model, fk_id)
                    value = str(value)
            response[field.name] = value
        for field in opts.local_many_to_many:
            value = getattr(self.model, field.name)
            value = value.values_list("pk", flat=True)
            response[field.name] = list(value)
        return response

    def serialize_queryset(self):
        """
        Check the fields of QuerySet and convert the data

        Returns: List
        """
        response = []
        for m in self.queryset:
            self.model = m
            m = self.serialize_model()
            response.append(m)

        del self.queryset
        return response


class QuerySetBasedXMLRPCSerializer(XMLRPCSerializer):
    """XMLRPC serializer specific for TestPlan

    To configure the serialization, developer can specify following class
    attribute, values_fields_mapping, m2m_fields, and primary_key.

    An unknown issue is that the primary key must appear in the
    values_fields_mapping. If doesn't, error would happen.
    """

    # Define the mapping relationship of names from ORM side to XMLRPC output
    # side.
    # Key is the name from ORM side.
    # Value is the name from the the XMLRPC output side
    values_fields_mapping: dict[str, tuple[str, Callable]] = {}

    # Define extra fields to allow provide extra fields in the serialization
    # result beside valid fields in database.
    extra_fields: dict[str, dict[str, str]] = {}

    def __init__(self, model_class, queryset):
        if model_class is None:
            raise ValueError("model_class should not be None")
        if queryset is None:
            raise ValueError("queryset should not be None")

        self.model_class = model_class
        self.queryset = queryset

    def get_extra_fields(self):
        """Get definition of extra fields mappings

        By default, user defined extra fields will be used. If not exist, an
        empty extra fields mapping is returned as to do nothing.

        This method can also be override in subclass to provide the extra
        fields programatically.
        """
        fields = getattr(self, "extra_fields", None)
        if fields is None:
            fields = {}
        return fields

    def _get_values_fields_mapping(self):
        """Return values fields mapping definition

        Values fields mapping can be also provided by overriding this method in
        subclass.

        :return: the mapping defined in class if presents, otherwise an empty
        dictionary object.
        :rtype: dict
        """
        return getattr(self.__class__, "values_fields_mapping", {})

    def _get_values_fields(self):
        """Return ORM side field names defined in the values fields mapping

        :return: list of fields in the ORM side. If `values_fields_mapping` is
        not defined in class, fields will be retrieved from coresponding Model
        class.
        :rtype: list

        """
        values_fields_mapping = self._get_values_fields_mapping()
        if values_fields_mapping:
            return values_fields_mapping.keys()
        else:
            return [field.name for field in self.model_class._meta.fields]

    def _get_m2m_fields(self):
        """Return names of fields with type ManyToManyField in ORM side

        By default, field names will be retreived from `m2m_fields` defined in
        class. If it does not present there, all fields with type
        ManyToManyField will be inspected and return names of all of them.

        Customized field names can be returned by overriding this method in
        subclass.

        :return: names of fields with type ManyToManyField
        :rtype: list
        """
        if hasattr(self.__class__, "m2m_fields"):
            return self.__class__.m2m_fields
        else:
            return tuple(field.name for field in self.model_class._meta.many_to_many)

    # TODO: how to deal with the situation that is primary key does not appear
    # in values fields, although such thing could not happen.
    def _get_primary_key_field(self):
        """Return the primary key field name

        The primary key field name can be specified by defining `primary_key`
        in class. Otherwise, QuerySetBasedXMLRPCSerializer will attempt to get
        the primary key field by inspecting Model's fields.

        This method can be overrided in subclass to provide custom primary key.

        :return: the name of primary key field
        :rtype: str
        :raises ValueError: if model does not have a primary key field during
        the process of inspecting primary key from model's field.
        """
        if hasattr(self.__class__, "primary_key"):
            return self.__class__.primary_key
        else:
            fields = [field.name for field in self.model_class._meta.fields if field.primary_key]
            if not fields:
                raise ValueError(
                    "Model %s has no primary key. You have to specify such "
                    "field manually." % self.model_class.__name__
                )
            return fields[0]

    def _query_m2m_field(self, field_name):
        """Query ManyToManyField order by model's pk

        Return value's format:
        {
            object_pk1: ({'pk': object_pk1, 'field_name': related_object_pk1},
                         {'pk': object_pk1, 'field_name': related_object_pk2},
                        ),
            object_pk2: ({'pk': object_pk2, 'field_name': related_object_pk3},
                         {'pk': object_pk2, 'field_name': related_object_pk4},
                         {'pk': object_pk3, 'field_name': related_object_pk5},
                        ),
            ...
        }

        :param str field_name: field name of a ManyToManyField
        :return: dictionary mapping between model's pk and related object's pk
        :rtype: dict
        """
        qs = self.queryset.values("pk", field_name).order_by("pk")
        return OrderedDict(
            {pk: tuple(values) for pk, values in groupby(qs.iterator(), operator.itemgetter("pk"))}
        )

    def _query_m2m_fields(self):
        m2m_fields = self._get_m2m_fields()
        return {field_name: self._query_m2m_field(field_name) for field_name in m2m_fields}

    def _get_single_field_related_object_pks(self, m2m_field_query, model_pk, field_name):
        return [item[field_name] for item in m2m_field_query[model_pk] if item[field_name]]

    def _get_related_object_pks(self, m2m_fields_query, model_pk, field_name):
        """Return related object pks from query result via ManyToManyFields

        Any object pk with value 0 or None values will be excluded in the final
        list.

        :param dict m2m_fields_query: the result returned from _query_m2m_fields
        :param model_pk: whose object's related object pks will be retrieved
        :type model_pk: int or long
        :param str field_name: field name of the related object
        :return: list of related objects' pks
        :rtype: list
        """
        data = m2m_fields_query[field_name]
        return self._get_single_field_related_object_pks(data, model_pk, field_name)

    def _handle_extra_fields(self, data):
        """Add extra fields

        Currently, alias is supported.

            - alias: add alias for any other serialized field name. If the
              specified field name does not exist in serialization result, it
              will be ignored.
        """
        extra_fields = self.get_extra_fields()

        for handle_name, value in extra_fields.items():
            if handle_name == "alias":
                for original_name, alias in value.items():
                    if original_name in data:
                        data[alias] = data[original_name]

    def serialize_queryset(self):
        """Core of QuerySet based serialization

        The process of serialization has following steps

        - Get data from database using QuerySet.values method
        - Transfer data to the output destiation according to serialization
          standard, where two things must be done,
          - field name must be replaced with right name rather than the
            internal name used for SQL query
          - some data must be converted in proper type. Currently, data with
            type datetime.datetime and datetime.timedelta must be converted to
            str (not UNICODE).
        - During the process of the above transfer, data associated with
          ManyToManyField should be retrieved from database and attached to
          each serialized data object.
        """
        qs = self.queryset.values(*self._get_values_fields())
        primary_key_field = self._get_primary_key_field()
        values_fields_mapping = self._get_values_fields_mapping()
        m2m_fields = self._get_m2m_fields()
        m2m_not_queried = True
        serialize_result = []

        # Handle ManyToManyFields, add such fields' values to final
        # serialization
        for row in qs.iterator():
            # Replace name from ORM side to the serialization side as expected
            new_serialized_data = {}
            if values_fields_mapping:
                for orm_name, serialize_info in values_fields_mapping.items():
                    serialize_name, conv_func = serialize_info
                    value = conv_func(row[orm_name])
                    new_serialized_data[serialize_name] = value
            else:
                # If no fields mapping, just use the original row as the
                # serialization result, and no data format conversion is
                # required obviously
                new_serialized_data.update(row)

            # Attach values of each ManyToManyField field
            # Lazy ManyToManyField query, to avoid query on ManyToManyFields if
            # serialization data is empty from database.
            if m2m_not_queried:
                m2m_fields_query = self._query_m2m_fields()
                m2m_not_queried = False
            model_pk = row[primary_key_field]
            for field_name in m2m_fields:
                related_object_pks = self._get_related_object_pks(
                    m2m_fields_query, model_pk, field_name
                )
                new_serialized_data[field_name] = related_object_pks

            # Finally, there might be some extra fields to added to final JSON
            # result to provide more custom information besides those data from
            # database. Add such extra fields in various ways that developers
            # define. This should be determined during the development
            # according to requirement.
            self._handle_extra_fields(new_serialized_data)

            serialize_result.append(new_serialized_data)

        return serialize_result


class TestPlanXMLRPCSerializer(QuerySetBasedXMLRPCSerializer):
    """XMLRPC serializer specific for TestPlan"""

    values_fields_mapping = {
        "create_date": ("create_date", datetime_to_str),
        "extra_link": ("extra_link", do_nothing),
        "is_active": ("is_active", do_nothing),
        "name": ("name", do_nothing),
        "plan_id": ("plan_id", do_nothing),
        "author": ("author_id", do_nothing),
        "author__username": ("author", to_str),
        "owner": ("owner_id", do_nothing),
        "owner__username": ("owner", to_str),
        "parent": ("parent_id", do_nothing),
        "parent__name": ("parent", encode_utf8),
        "product": ("product_id", do_nothing),
        "product__name": ("product", encode_utf8),
        "product_version": ("product_version_id", do_nothing),
        "product_version__value": ("product_version", encode_utf8),
        "type": ("type_id", do_nothing),
        "type__name": ("type", encode_utf8),
    }

    extra_fields = {
        "alias": {"product_version": "default_product_version"},
    }

    m2m_fields = ("attachments", "case", "component", "env_group", "tag")


class TestCaseRunXMLRPCSerializer(QuerySetBasedXMLRPCSerializer):
    """XMLRPC serializer specific for TestCaseRun"""

    values_fields_mapping = {
        "case_run_id": ("case_run_id", do_nothing),
        "case_text_version": ("case_text_version", do_nothing),
        "close_date": ("close_date", datetime_to_str),
        "environment_id": ("environment_id", do_nothing),
        "notes": ("notes", do_nothing),
        "running_date": ("running_date", datetime_to_str),
        "sortkey": ("sortkey", do_nothing),
        "assignee": ("assignee_id", do_nothing),
        "assignee__username": ("assignee", to_str),
        "build": ("build_id", do_nothing),
        "build__name": ("build", encode_utf8),
        "case": ("case_id", do_nothing),
        "case__summary": ("case", encode_utf8),
        "case_run_status": ("case_run_status_id", do_nothing),
        "case_run_status__name": ("case_run_status", encode_utf8),
        "run": ("run_id", do_nothing),
        "run__summary": ("run", encode_utf8),
        "tested_by": ("tested_by_id", do_nothing),
        "tested_by__username": ("tested_by", to_str),
    }


class TestRunXMLRPCSerializer(QuerySetBasedXMLRPCSerializer):
    """Serializer for TestRun"""

    values_fields_mapping = {
        "auto_update_run_status": ("auto_update_run_status", do_nothing),
        "environment_id": ("environment_id", do_nothing),
        "estimated_time": ("estimated_time", timedelta_to_str),
        "notes": ("notes", do_nothing),
        "plan_text_version": ("plan_text_version", do_nothing),
        "run_id": ("run_id", do_nothing),
        "start_date": ("start_date", datetime_to_str),
        "stop_date": ("stop_date", datetime_to_str),
        "summary": ("summary", do_nothing),
        "build": ("build_id", do_nothing),
        "build__name": ("build", encode_utf8),
        "default_tester": ("default_tester_id", do_nothing),
        "default_tester__username": ("default_tester", to_str),
        "manager": ("manager_id", do_nothing),
        "manager__username": ("manager", to_str),
        "plan": ("plan_id", do_nothing),
        "plan__name": ("plan", encode_utf8),
        "product_version": ("product_version_id", do_nothing),
        "product_version__value": ("product_version", encode_utf8),
    }


class TestCaseXMLRPCSerializer(QuerySetBasedXMLRPCSerializer):
    """Serializer for TestCase"""

    values_fields_mapping = {
        "alias": ("alias", do_nothing),
        "arguments": ("arguments", do_nothing),
        "case_id": ("case_id", do_nothing),
        "create_date": ("create_date", datetime_to_str),
        "estimated_time": ("estimated_time", timedelta_to_str),
        "extra_link": ("extra_link", do_nothing),
        "is_automated": ("is_automated", do_nothing),
        "is_automated_proposed": ("is_automated_proposed", do_nothing),
        "notes": ("notes", do_nothing),
        "requirement": ("requirement", do_nothing),
        "script": ("script", do_nothing),
        "summary": ("summary", do_nothing),
        "author": ("author_id", do_nothing),
        "author__username": ("author", to_str),
        "case_status": ("case_status_id", do_nothing),
        "case_status__name": ("case_status", encode_utf8),
        "category": ("category_id", do_nothing),
        "category__name": ("category", encode_utf8),
        "default_tester": ("default_tester_id", do_nothing),
        "default_tester__username": ("default_tester", to_str),
        "priority": ("priority_id", do_nothing),
        "priority__value": ("priority", encode_utf8),
        "reviewer": ("reviewer_id", do_nothing),
        "reviewer__username": ("reviewer", to_str),
    }


class ProductXMLRPCSerializer(QuerySetBasedXMLRPCSerializer):
    """Serializer for Product"""

    values_fields_mapping = {
        "id": ("id", do_nothing),
        "name": ("name", do_nothing),
        "description": ("description", do_nothing),
        "milestone_url": ("milestone_url", do_nothing),
        "disallow_new": ("disallow_new", do_nothing),
        "vote_super_user": ("vote_super_user", do_nothing),
        "max_vote_super_bug": ("max_vote_super_bug", do_nothing),
        "votes_to_confirm": ("votes_to_confirm", do_nothing),
        "default_milestone": ("default_milestone", do_nothing),
        "classification": ("classification_id", do_nothing),
        "classification__name": ("classification", encode_utf8),
    }


class TestBuildXMLRPCSerializer(QuerySetBasedXMLRPCSerializer):
    """Serializer for TestBuild"""

    values_fields_mapping = {
        "build_id": ("build_id", do_nothing),
        "description": ("description", do_nothing),
        "is_active": ("is_active", do_nothing),
        "milestone": ("milestone", do_nothing),
        "name": ("name", do_nothing),
        "product": ("product_id", do_nothing),
        "product__name": ("product", encode_utf8),
    }
