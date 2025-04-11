# -*- coding: utf-8 -*-

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Index
from tcms.core.models import TCMSContentTypeBaseModel

from .managers import TCMSLogManager

# Create your models here.
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

class TCMSLogModel(TCMSContentTypeBaseModel):
    # Bên trong class TCMSLogModel:
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    date = models.DateTimeField(auto_now_add=True)
    action = models.TextField()
    field = models.CharField(max_length=50, default="")
    original_value = models.TextField(default="")
    new_value = models.TextField(default="")

    who = models.ForeignKey("auth.User", related_name="log_who", on_delete=models.CASCADE)

    objects = TCMSLogManager()

    class Meta:
        abstract = False
        db_table = "tcms_logs"
        indexes = [
            Index(fields=['object_id', 'content_type']),
        ]

    def __str__(self):
        return self.action

    @classmethod
    def get_logs_for_model(cls, model_class, object_id):
        ct = ContentType.objects.get_for_model(model_class)
        return cls.objects.filter(content_type=ct, object_id=object_id)
