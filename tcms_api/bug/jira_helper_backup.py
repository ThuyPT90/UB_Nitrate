# filepath: /home/thuypt90/UB_Nitrate/tcms_api/bug/jira_helper_backup.py
# jira_helper_backup.py: Backup of jira_helper.py

import re
import requests
from datetime import datetime
from requests.auth import HTTPBasicAuth
from config import JIRA_URL, JIRA_USER, JIRA_PASS, JIRA_PROJECT_KEY, JIRA_ISSUE_TYPE

def parse_jira_fields_from_comment(comment: str) -> dict:
    fields = {}
    patterns = {
        "assignee": r"assignee:\s*(\S+)",
        "epic_id": r"epic_id:\s*(\S+)",
        "due_date": r"due_date:\s*(\d{4}-\d{2}-\d{2})",
        "expected": r"expected:\s*(.+)",
        "start_date": r"start_date:\s*(\d{4}-\d{2}-\d{2})"
    }
    for field, pattern in patterns.items():
        match = re.search(pattern, comment, re.IGNORECASE)
        if match:
            fields[field] = match.group(1).strip()

    now_str = datetime.now().strftime("%Y-%m-%d")
    fields.setdefault("assignee", JIRA_USER)
    fields.setdefault("epic_id", "EPIC-UNKNOWN")
    fields.setdefault("due_date", now_str)
    fields.setdefault("expected", "Không có mô tả kết quả dự kiến")
    fields.setdefault("start_date", now_str)

    fields["description"] = (
        f"*TestCase Comment:*<br/>{comment}<br/><br/>"
        f"*Mô tả lỗi:* {fields['expected']}<br/>"
        f"*Ngày bắt đầu:* {fields['start_date']}<br/>"
    )

    return fields
def create_jira_bug(case_id, notes, fields):
    print(f"\n📌 Debug: case_id={case_id}")
    print(f"📄 Fields trích xuất: {fields}")
    print(f"🌐 Jira URL: {JIRA_URL}")
    print(f"👤 Jira User: {JIRA_USER}")
    print(f"🔐 Jira Password (ẩn): {JIRA_PASS[:3]}***")

    summary = f"[AUTO][TC#{case_id}] {fields['expected'][:80]}"

    bug_data = {
        "fields": {
            "project": {"key": JIRA_PROJECT_KEY},
            "summary": summary,
            "description": fields["description"],
            "issuetype": {"name": JIRA_ISSUE_TYPE},
            "assignee": {"name": fields["assignee"]},
            "customfield_10109": fields["epic_id"],
            "duedate": fields["due_date"],
            "customfield_10401": fields["expected"],
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