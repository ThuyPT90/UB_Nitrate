# jira_helper.py: gửi bug lên Jira
import json  # ✅ đang dùng json.dumps nhưng chưa import
import re
import requests
from datetime import datetime
from requests.auth import HTTPBasicAuth
from tcms_api.bug.config import JIRA_URL, JIRA_USER, JIRA_PASS, JIRA_PROJECT_KEY, JIRA_ISSUE_TYPE


def parse_jira_fields_from_comment(comment: str, testcase, instance) -> dict:
    fields = {}
    patterns = {
        "assignee": r"assignee:\s*(\S+)",
        "epic_id": r"epic_id:\s*(\S+)",
        "due_date": r"due_date:\s*(\d{4}-\d{2}-\d{2})",
        "summary": r"summary:\s*(.+)",
        "start_date": r"start_date:\s*(\d{4}-\d{2}-\d{2})",
        "expected_result": r"expected_result:\s*(.+)",
        "pre_condition": r"pre_condition:\s*(.+)",
        "step": r"step:\s*(.+)",
        "evidence": r"evidence:\s*(.+)"
    }
    for field, pattern in patterns.items():
        match = re.search(pattern, comment, re.IGNORECASE)
        if match:
            fields[field] = match.group(1).strip()

    now_str = datetime.now().strftime("%Y-%m-%d")
    fields.setdefault("assignee", JIRA_USER)
    fields.setdefault("epic_id", "PAYT-875")
    fields.setdefault("due_date", now_str)
    fields.setdefault("summary", "Không có tiêu đề bug")
    fields.setdefault("expected_result", "Không có mô tả kết quả dự kiến")
    fields.setdefault("step", "")
    fields["case_id"] = testcase.pk
    fields["case_run_id"] = instance.pk
    # fields["step"] = fields.get("step", "").strip() or (testcase.actions or "")
    # fields["pre_condition"] = fields.get("pre_condition", "").strip() or (testcase.setup or "")
    # fields["expected_result"] = fields.get("expected_result", "").strip() or (testcase.expected_results or "")
    now_str = datetime.now().strftime("%Y-%m-%d")
    fields["start_date"] = fields.get("start_date", "").strip()
    if not fields["start_date"]:
        fields["start_date"] = now_str

    fields["description"] = (
        f"*TestCase ID:* {fields.get('case_id', '')}<br/>"
        f"*Case Run ID:* {fields.get('case_run_id', '')}<br/><br/>"
        f"*Điều kiện cần thiết:*<br/>{fields.get('pre_condition', '')}<br/><br/>"
        f"*Bước thực hiện:*<br/>{fields.get('step', '')}<br/><br/>"
        f"*Kết quả mong muốn:*<br/>{fields['expected_result']}<br/>"
        f"*Link evidence:*<br/>{fields.get('evidence', '')}<br/><br/>"
        # f"*Ghi chú ban đầu:*<br/>{comment}<br/>"
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
        elif response.status_code == 401:
            print("🔒 Lỗi 401 - Sai username/password Jira.")
        elif response.status_code == 403:
            print("🚫 Lỗi 403 - Không đủ quyền tạo bug.")
        else:
            print(f"❌ Tạo bug thất bại: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"💥 Lỗi khi kết nối Jira: {e}")
   
    
