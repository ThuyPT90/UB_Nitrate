import os
print(f"🔁 [AutoBugPlugin] Loaded by PID {os.getpid()}")
print("✅ Plugin auto_bug_plugin.py đã được import thành công!")
from tcms.testcases.models import TestCase
from tcms.testruns.models import TestCaseRun
from tcms.testruns.status import TestCaseRunStatus
from django.contrib.contenttypes.models import ContentType
from tcms.comments.models import Comment
from tcms_api.bug.jira_helper import get_issue_status

try:
    from tcms_api.bug.jira_helper import create_jira_bug, parse_jira_fields_from_comment

    print("✅ Đã nạp thành công bug.nitrate_helper")
except ImportError as e:
    print("⚠️ Không tìm thấy bug.nitrate_helper – plugin auto bug sẽ không hoạt động!")
    print(f"Lỗi: {e}")
    create_jira_bug = None
    parse_jira_fields_from_comment = None   # ✅ Thêm dòng này để tránh lỗi "not defined"

def extract_summary_expected(comment_text):
    summary = ""
    expected = ""
    for line in comment_text.splitlines():
        line = line.strip()
        if line.lower().startswith("summary:"):
            summary = line[8:].strip()
        elif line.lower().startswith("expected_result:"):
            expected = line[16:].strip()
    return summary, expected

def receiver(context): 

    instance = context.get("instance")
    print("🐞 [AutoBugPlugin] 👉 receiver(context) được gọi!")

    if instance is None:
        print("⚠️ Không tìm thấy instance trong context!")
        return
    if getattr(instance, '_auto_bug_handled', False):
        print("⛔️ Đã xử lý bug cho TestCaseRun này – bỏ qua.")
        return
    instance._auto_bug_handled = True
    signal = context.get("signal")
     # 👉 Chỉ xử lý nếu là TestCaseRun
    print(f"🔔 Signal nhận được: {getattr(signal, '__name__', str(signal))}, Model: {type(instance).__name__}")

    # Kiểm tra đúng model và signal là testcase run không
    if not isinstance(instance, TestCaseRun):
        print("⚠️Kiểm tra nếu không phải TestCaseRun – bỏ qua.")
        return

    # ✅ In trạng thái trước khi so sánh
    print(f"📌 TestCaseRun case_run_status_id = {instance.case_run_status_id}")
    if instance.case_run_status_id != TestCaseRunStatus.FAILED:
        print("⚠️ Không phải TestCaseRun FAILED – bỏ qua.")
        return
    content_type = ContentType.objects.get_for_model(instance)
    existing_bug_comments = Comment.objects.filter(
        content_type=content_type,
        object_pk=str(instance.pk),
        comment__icontains="JIRA BUG:"
    ).order_by('-submit_date')

    print(f"🧪 Số comment Jira BUG tìm được: {existing_bug_comments.count()}")
    for c in existing_bug_comments:
        print(f"📝 Cmt: {c.comment[:100]}...")  # In 100 ký tự đầu

    print(f"🔍 content_type ID = {content_type.id}, object_pk = {instance.pk}")
    if existing_bug_comments.exists():
        print("🔁 Đã có comment chứa Jira bug – bỏ qua.")
        return
    
    # Lấy comment mới nhất để phân tích nội dung tạo bug
    latest_comment = Comment.objects.filter(
        content_type=content_type,
        object_pk=str(instance.pk)
    ).order_by('-submit_date').first()
    latest_text = latest_comment.comment if latest_comment else ""
    summary_new, expected_new = extract_summary_expected(latest_text)
    print(f"📋 Nội dung comment gần nhất:\n{latest_text}")
    print(f"📝 Summary mới: {summary_new}")
    print(f"✅ Expected mới: {expected_new}")
    if not summary_new or not expected_new:
        print("⚠️ Thiếu summary hoặc expected_result trong comment – không tạo Jira bug.")
        return

    #  ✅ Kiểm tra comment cũ có chứa bug Jira và so sánh nội dung
    existing_comments = Comment.objects.filter(
        content_type=content_type,
        object_pk=str(instance.pk)
    )
    for c in existing_comments:
        if "JIRA BUG:" in c.comment:
            print(f"Có bug Jira")
            return
        latest_bug_comment = Comment.objects.filter(
            content_type=content_type,
            object_pk=str(instance.pk),
            comment__icontains="JIRA BUG:"
        ).order_by('-submit_date').first()
        if latest_bug_comment:
            summary_old, expected_old = extract_summary_expected(latest_bug_comment.comment)
            print(f"📋 So sánh với bug cũ – Summary: {summary_old} | Expected: {expected_old}")    
            if summary_old == summary_new and expected_old == expected_new:
                print("🔁 Nội dung bug giống nhau – không tạo lại.")
                return

    print("🆕 Nội dung bug khác – bắt đầu tạo Jira Bug...")  
    testcase = instance.case
    notes = latest_text
    print(f"📝 TestCase Notes: {notes}")
    print(f"🐞 AutoBug: TestCase #{testcase.pk} FAILED – đang tạo Jira Bug...")

    if create_jira_bug and parse_jira_fields_from_comment:
        try:
            print(f"📌 CaseRun ID = {instance.pk}, Case ID = {instance.case.pk}")
            # Đặt cờ đã xử lý để tránh bị gọi lại
            setattr(instance, '_auto_bug_handled', True)
            fields = parse_jira_fields_from_comment(notes, testcase, instance)

            # 📝 In ra trước nội dung mô tả trước khi gửi lên Jira
            print("\n📋 Mô tả sẽ gửi lên Jira:")
            print(fields["description"])  # 👈 in nội dung mô tả bug
            
            # 🛑 Tạm thời không gửi bug lên Jira
            # print("🛑 Đã dừng lại trước khi tạo Jira bug – chỉ hiển thị nội dung để kiểm tra.")
            print("🚀 Bắt đầu gọi API tạo bug Jira...")
            bug_url = create_jira_bug(testcase.pk, notes, fields)
            print(f"🐞 Đã tạo bug: {bug_url}")
            # ✅ Ghi bug_url vào comment gần nhất
            if latest_comment:
                latest_comment.comment += f"\nJIRA BUG: {bug_url}"
                latest_comment.save()
                print("✅ Đã thêm thông tin Jira BUG vào comment gần nhất.")
            else:
                print("⚠️ Không tìm thấy comment gần nhất để cập nhật.")
        except Exception as e:
            print(f"❌ AutoBug ERROR: {e}")
        # # ✅ Ghi comment sau khi bug tạo thành công – đảm bảo luôn được thực hiện
        # user = context.get("user")
        # user_id = user.id if user else 1

        # try:
        #     Comment.objects.create(
        #         content_type=content_type,
        #         object_pk=str(instance.pk),
        #         user_id=user_id,
        #         comment=f"JIRA BUG: {bug_url}\nsummary: {summary_new}\nexpected_result: {expected_new}"
        #     )
        #     print("📝 Đã ghi comment Jira BUG vào TestCaseRun thành công.")
        # except Exception as e:
        #     print(f"⚠️ Ghi comment thất bại: {e}")
    else:
        print("🚫 Hàm tạo Jira Bug chưa sẵn sàng – bỏ qua.")


