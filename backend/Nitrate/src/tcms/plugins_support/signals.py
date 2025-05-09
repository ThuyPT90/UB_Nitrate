# -*- coding: utf-8 -*-
from typing import Optional, Type
from django.db.models import Model, signals
from tcms.core.models import signals as tcms_signals
from tcms.plugins_support.processors import pstp

from django.db.models.signals import post_save
from django.dispatch import receiver as django_receiver
from tcms.testruns.models import TestCaseRun

@django_receiver(post_save, sender=TestCaseRun)
def trigger_autobug_on_save(sender, instance, **kwargs):
    # Tự động đẩy signal update khi test case run được lưu
    pstp.push(sender, instance, "update")

# Initial the registered models
REGISTERED_MODELS: dict[Type[Model], "GlobalSignalProcessor"] = {}


# The global signal processor
class GlobalSignalProcessor:
    """
    This class is responsible for handling all of signals trigger by model
    """

    def __init__(self, model):
        self.model = model

    def initial_processor(self, entry):
        pstp.push(self.model, entry, tcms_signals.initial)

    def save_processor(self, entry, created):
        if created:
            pstp.push(self.model, entry, tcms_signals.create)
        pstp.push(self.model, entry, tcms_signals.update)

    def delete_processor(self, entry):
        pstp.push(self.model, entry, tcms_signals.delete)

    def apply_parents(self, instance, func):
        """
        Iterates through all non-abstract inherited parents and applies the
        supplied function
        """
        for field in instance._meta.parents.values():
            if field and getattr(instance, field.name, None):
                func(getattr(instance, field.name))


# The signal handlers
def initial_signal_handler(instance, **kwargs):
    if instance.pk is not None:
        handler = REGISTERED_MODELS[type(instance)]
        handler.initial_processor(instance)
        handler.apply_parents(instance, handler.initial_processor)


def save_signal_handler(instance, created, **kwargs):
    REGISTERED_MODELS[type(instance)].save_processor(instance, created)
     # ✅ THÊM DÒNG NÀY
    from .processors import pstp
    pstp.push(type(instance), instance, "update" if not created else "create")

def delete_signal_handler(instance, **kwargs):
    REGISTERED_MODELS[type(instance)].delete_processor(instance)
    # ✅ THÊM DÒNG NÀY
    from .processors import pstp
    pstp.push(type(instance), instance, "delete")

# Bind the signals and the models
def register_model(model: Type[Model], sp: Optional[Type[GlobalSignalProcessor]] = None):
    print(f"✅ đang gọi register_model")
    if model in REGISTERED_MODELS:
        return
    for parent in model._meta.parents.keys():
        register_model(parent, sp)
    if sp is None:
        sp = GlobalSignalProcessor
    signals.post_init.connect(initial_signal_handler, sender=model)
    signals.post_save.connect(save_signal_handler, sender=model)
    signals.post_delete.connect(delete_signal_handler, sender=model)
    REGISTERED_MODELS[model] = sp(model)
    print(f"✅ Đã gọi register_model cho: {model}")