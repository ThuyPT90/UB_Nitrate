# jira_helper.py: gửi bug lên Jira

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
        "due_date": r"due_date:\s*(\S+)",
        "expected": r"expected:\s*(.+)",
        "start_date": r"start_date:\s*(\S+)"
    }
    for field, pattern in patterns.items():
        match = re.search(pattern, comment)
        if match:
            fields[field] = match.group(1)
   # Nếu bạn cần summary/description từ comment, gán lại đúng biến
    fields['summary'] = comment[:100]  # lấy 100 ký tự đầu làm summary
    fields['description'] = comment
    return fields
def create_jira_bug(case_id, notes, fields):
    print(f"Debug: case_id={case_id}, notes={notes}, fields={fields}")
    print(f"Debug: JIRA_URL={JIRA_URL}, JIRA_USER={JIRA_USER}, JIRA_PROJECT_KEY={JIRA_PROJECT_KEY}")

    bug_data = {
        "fields": {
            "project": {"key": JIRA_PROJECT_KEY},
            "summary": f"[AUTO] Bug from TestCase #{case_id}",
            "description": f"Tự động tạo từ Nitrate - Test case ID: {case_id}<br/>{notes}",
            "issuetype": {"name": JIRA_ISSUE_TYPE},
            "assignee": {"name": fields.get("assignee", JIRA_USER)},
            "customfield_10109": fields.get("epic_id"),  # Epic ID
            "duedate": fields.get("due_date", datetime.now().strftime("%Y-%m-%d")),
            "customfield_10401": fields.get("expected", "Không có mô tả kết quả dự kiến"),
            "customfield_10504": fields.get("start_date", datetime.now().strftime("%Y-%m-%d"))
        }
    }
    # ✅ THÊM DEBUG: Hiển thị dữ liệu request và auth
    print("\n🧩 DEBUG: Đang gửi dữ liệu tạo bug lên Jira...")
    print("🔗 URL:", JIRA_URL)
    print("👤 Username:", JIRA_USER)
    print("🔐 Password (ẩn):", JIRA_PASS[:3] + "***")
 
    # In payload trước khi gửi yêu cầu
    print(f"Request payload: {bug_data}")

    response = requests.post(
        JIRA_URL,
        auth=HTTPBasicAuth(JIRA_USER, JIRA_PASS),
        json=bug_data,
        headers={"Content-Type": "application/json"}
    )

    # In phản hồi từ Jira API
    print(f"Response: {response.status_code} - {response.text}")

    print(f"✅ Bug created for case #{case_id}: {response.status_code} - {response.text}")
