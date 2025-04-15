print("✅ Đăng ký model TestCaseRun với signal...")
from tcms.testruns.models import TestCaseRun
from tcms.plugins_support.signals import register_model

print("✅ Đăng ký model TestCaseRun với signal...")
register_model(TestCaseRun)
print("✅ auto_bug_plugin đã gọi register_model(TestCaseRun)")    