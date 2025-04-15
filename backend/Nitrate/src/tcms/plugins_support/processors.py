# -*- coding: utf-8 -*-
import threading
from django.conf import settings


class NewThread(threading.Thread):
    def __init__(self, command, args):
        self.command = command
        self.args = args
        super().__init__()

    def run(self):
        # The actual code we want to run
        return self.command(self.args)


class PushSignalToPlugins:
    def __init__(self):
        self.plugins = []

    def import_plugins(self):
        from importlib import import_module

        plugins = getattr(settings, "SIGNAL_PLUGINS", [])
        for plugin in plugins:
            if plugin == "tcms.plugins_support.auto_bug_plugin":
                # ✅ Tránh import vòng
                import tcms.plugins_support.auto_bug_plugin as auto_plugin
                self.plugins.append(auto_plugin)
            else:
                self.plugins.append(import_module(plugin))

    def push(self, model, instance, signal):
        for p in self.plugins:
            NewThread(p.receiver, {"model": model, "instance": instance, "signal": signal}).start()


# Create the PushSignalToPlugins instance
pstp = PushSignalToPlugins()
pstp.import_plugins()
