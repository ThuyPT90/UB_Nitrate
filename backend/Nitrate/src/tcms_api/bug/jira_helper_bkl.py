# jira_helper.py: gửi bug lên Jira
import json  # ✅ đang dùng json.dumps nhưng chưa import
import re
import requests
from datetime import datetime
from requests.auth import HTTPBasicAuth
from tcms_api.bug.config import JIRA_URL, JIRA_USER, JIRA_PASS, JIRA_PROJECT_KEY, JIRA_ISSUE_TYPE

def strip_paragraph_tags(text):
    # Loại bỏ thẻ <p> và thay bằng <br/>
    return re.sub(r'</?p[^>]*>', '<br/>', text or "")

def parse_jira_fields_from_comment(comment: str, testcase, instance) -> dict:
    comment = comment.replace("\r\n", "\n").strip()
    fields = {}
    patterns = {
        "assignee": r"assignee:\s*([^\n\r]+)",
        "due_date": r"due_date:\s*(\d{4}-\d{2}-\d{2})$",
        "summary": r"summary:\s*([^\n\r]+)",
        "start_date": r"start_date:\s*(\d{4}-\d{2}-\d{2})$",
        "expected_result": r"expected_result:\s*((?:.|\n)+?)(?=\n(?:assignee|epic_id|due_date|summary|pre_condition|step|evidence|start_date):|$)",
        "pre_condition": r"pre_condition:\s*((?:.|\n)+?)(?=\n(?:assignee|epic_id|due_date|summary|expected_result|step|evidence|start_date):|$)",
        "step": r"step:\s*((?:.|\n)+?)(?=\n(?:assignee|epic_id|due_date|summary|expected_result|pre_condition|evidence|start_date):|$)",
        "evidence": r"evidence:\s*((?:.|\n)+?)",
        "epic_id": r"epic_id:\s*([^\n\r]+)"
    }
   
    for field, pattern in patterns.items():
        match = re.search(pattern, comment, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if match:
            fields[field] = match.group(1).strip()
    print("📋 Nội dung comment nhận được:\n", comment)
    now_str = datetime.now().strftime("%Y-%m-%d")
    fields.setdefault("assignee", JIRA_USER)
    fields.setdefault("epic_id", "PAYT-875")
    fields.setdefault("due_date", now_str)
    fields.setdefault("summary", "Không có tiêu đề bug")
    # ✅ Lấy từ testcase nếu chưa có
    fields["case_id"] = testcase.pk
    fields["case_run_id"] = instance.pk
    tc_text = testcase.text.order_by('-case_text_version').first()
    fields["step"] = fields.get("step", "").strip() or (tc_text.action or "")
    fields["pre_condition"] = fields.get("pre_condition", "").strip() or (tc_text.setup or "")
    fields["expected_result"] = fields.get("expected_result", "").strip() or (tc_text.effect or "")
    fields["start_date"] = fields.get("start_date", "").strip() or now_str

    # ✅ Làm sạch HTML nếu cần
    fields["step"] = strip_paragraph_tags(fields["step"])
    fields["pre_condition"] = strip_paragraph_tags(fields["pre_condition"])
    fields["expected_result"] = strip_paragraph_tags(fields["expected_result"])

    fields["description"] = (
        f"*TestCase ID:* {fields.get('case_id', '')}"
        f"*Case Run ID:* {fields.get('case_run_id', '')}<br/><br/>"
        f"*Điều kiện cần thiết:*{fields.get('pre_condition', '').replace('\n', '<br/>')}<br/><br/>"
        f"*Bước thực hiện:*<br/>{fields.get('step', '').replace('\n', '<br/>')}<br/><br/>"
        f"*Kết quả mong muốn:*<br/>{fields['expected_result'].replace('\n', '<br/>')}<br/>"
        f"*Link evidence:*<br/>{fields.get('evidence', '')}<br/><br/>"
    )

    return fields

def create_jira_bug(case_id, notes, fields):
    print(f"\n📌 Debug: case_id={case_id}")
    print(f"📄 Fields trích xuất: {fields}")
    print(f"🌐 Jira URL: {JIRA_URL}")
    print(f"👤 Jira User: {JIRA_USER}")
    print(f"🔐 Jira Password (ẩn): {JIRA_PASS[:3]}***")

    summary = f"[AUTO][TC#{case_id}] {fields['summary'][:80]}"

    bug_data = {
        "fields": {
            "project": {"key": JIRA_PROJECT_KEY},
            "summary": summary,
            "description": fields["description"],
            "issuetype": {"name": JIRA_ISSUE_TYPE},
            "assignee": {"name": fields["assignee"]},
            "customfield_10109": fields["epic_id"],
            "duedate": fields["due_date"],
            "customfield_10401": fields["expected_result"],
            "customfield_10504": fields["start_date"]
        }
    }

    print("\n🚀 Đang gửi dữ liệu tạo bug lên Jira...")
    print("📦 Payload:", bug_data)
    
    try:
        response = requests.post(
            JIRA_URL,
            auth=HTTPBasicAuth(JIRA_USER, JIRA_PASS),
            json=bug_data,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 201:
            issue_key = response.json().get("key")
            print(f"✅ Bug tạo thành công: {issue_key} (TestCase #{case_id})")
            return issue_key
        elif response.status_code == 400:
            print("⚠️ Lỗi 400 - Dữ liệu không hợp lệ.")
            try:
                error_data = response.json()
                if "errorMessages" in error_data:
                    print("🔍 Thông báo lỗi chi tiết:")
                    for msg in error_data["errorMessages"]:
                        print(f" - {msg}")
                if "errors" in error_data:
                    print("🧩 Trường lỗi chi tiết:")
                    for field, msg in error_data["errors"].items():
                        print(f" - {field}: {msg}")
            except Exception as e:
                print(f"⚠️ Không thể phân tích lỗi chi tiết: {e}")
        elif response.status_code == 401:
            print("🔒 Lỗi 401 - Sai username/password Jira.")
        elif response.status_code == 403:
            print("🚫 Lỗi 403 - Không đủ quyền tạo bug.")
        else:
            print(f"❌ Tạo bug thất bại: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"💥 Lỗi khi kết nối Jira: {e}")
   
    
