# Django settings for devel env.

from tcms.settings.common import *
import os
from dotenv import load_dotenv

load_dotenv()
DB_ENGINE = os.getenv("NITRATE_DB_ENGINE", "mysql")
# Debug settings
DEBUG = True

# 👇 Thêm đoạn này để đọc biến môi trường từ common.py
from .common import DB_ENGINE

DATABASES = {
    "default": {
        "ENGINE": SUPPORTED_DB_ENGINES[DB_ENGINE],
        "NAME": env.get("NITRATE_DB_NAME", "nitrate"),
        "USER": env.get("NITRATE_DB_USER", "nitrate"),
        "PASSWORD": env.get("NITRATE_DB_PASSWORD", "nitrate"),
        "HOST": env.get("NITRATE_DB_HOST", ""),
        "PORT": env.get("NITRATE_DB_PORT", ""),
    },
}

SECRET_KEY = "secret-key-for-dev-only"  # nosec

# django-debug-toolbar settings
MIDDLEWARE += ("debug_toolbar.middleware.DebugToolbarMiddleware",)

INSTALLED_APPS += (
    "debug_toolbar",
    )

DEBUG_TOOLBAR_CONFIG = {"INTERCEPT_REDIRECTS": False}

FILE_UPLOAD_DIR = os.path.join(TCMS_ROOT_PATH, "..", "uploads")

ASYNC_TASK = "DISABLED"
SIGNAL_PLUGINS = [
    "tcms.plugins_support.auto_bug_plugin",
]