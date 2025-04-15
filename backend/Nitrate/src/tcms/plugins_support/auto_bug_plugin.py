import os
print(f"🔁 [AutoBugPlugin] Loaded by PID {os.getpid()}")
print("✅ Plugin auto_bug_plugin.py đã được import thành công!")
from tcms.testcases.models import TestCase
from tcms.testruns.models import TestCaseRun
from tcms.testruns.status import TestCaseRunStatus
from django.contrib.contenttypes.models import ContentType
from tcms.comments.models import Comment

try:
    from tcms_api.bug.jira_helper import create_jira_bug, parse_jira_fields_from_comment

    print("✅ Đã nạp thành công bug.nitrate_helper")
except ImportError as e:
    print("⚠️ Không tìm thấy bug.nitrate_helper – plugin auto bug sẽ không hoạt động!")
    print(f"Lỗi: {e}")
    create_jira_bug = None
    parse_jira_fields_from_comment = None   # ✅ Thêm dòng này để tránh lỗi "not defined"

def receiver(context): 
    print("🐞 AutoBugPlugin đã được kích hoạt bởi post_save signal")
    print("🐞 [AutoBugPlugin] 👉 receiver(context) được gọi!")
    print("📦 Context nhận được:", context)
    print("🧪 Plugin auto_bug_plugin đang xử lý context")

    instance = context.get("instance")
    signal = context.get("signal")
     # 👉 Chỉ xử lý nếu là TestCaseRun
    if not isinstance(instance, TestCaseRun):
        print(f"⚠️ Bỏ qua vì không phải TestCaseRun: {type(instance)}")
        return
    
    print(f"🔔 Tín hiệu nhận: {signal}, Model: {type(instance).__name__}")
    if not isinstance(instance, TestCaseRun):
        print("⚠️ Không phải TestCaseRun – bỏ qua.")
        return
    print(f"📌 TestCaseRun case_run_status_id = {instance.case_run_status_id}")

    # Kiểm tra đúng model và signal là UPDATE
    if not isinstance(instance, TestCaseRun):
        print("⚠️ Không phải TestCaseRun – bỏ qua.")
        return
    if signal != "update":
        return
    
    # Chỉ trigger khi FAILED
    if instance.case_run_status_id != TestCaseRunStatus.FAILED:
        print(f"📌 TestCaseRun case_run_status_id = {instance.case_run_status_id}")
        print("✅ Không phải trạng thái FAILED – bỏ qua.")
        return
    
    testcase = instance.case

    content_type = ContentType.objects.get_for_model(instance)
    latest_comment = Comment.objects.filter(
        content_type=content_type,
        object_pk=str(instance.pk)
    ).order_by('-submit_date').first()

    notes = latest_comment.comment if latest_comment else ""
    
    print(f"📝 TestCase Notes: {notes}")
    print(f"🐞 Đã phát hiện TestCaseRun FAILED – sắp tạo bug cho testcase #{testcase.pk}")
    print(f"🐞 AutoBug: TestCase #{testcase.pk} FAILED – đang tạo Jira Bug...")
        
    if create_jira_bug and parse_jira_fields_from_comment:
        try:
            print(f"📌 CaseRun ID = {instance.pk}, Case ID = {instance.case.pk}")
            fields = parse_jira_fields_from_comment(notes, testcase, instance)
            print("📋 Mô tả bug gửi đi:")
            for k, v in fields.items():
                print(f" - {k}: {v}")
            
            # 📝 In ra trước nội dung mô tả trước khi gửi lên Jira
            print("\n📋 Mô tả sẽ gửi lên Jira:")
            print(fields["description"])  # 👈 in nội dung mô tả bug

            # 🛑 Tạm thời không gửi bug lên Jira
            create_jira_bug(testcase.pk, notes, fields)
            print("🚀 Bắt đầu gọi API tạo bug Jira...")
            bug_url = create_jira_bug(testcase.pk, notes, fields)
            print(f"🐞 Đã tạo bug: {bug_url}")
            # print("🛑 Đã dừng lại trước khi tạo Jira bug – chỉ hiển thị nội dung để kiểm tra.")
        except Exception as e:
            print(f"❌ AutoBug ERROR: {e}")
    else:
        print("🚫 Hàm tạo Jira Bug chưa sẵn sàng – bỏ qua.")
