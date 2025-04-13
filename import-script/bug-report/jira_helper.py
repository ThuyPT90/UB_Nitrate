# jira_helper.py: gửi bug lên Jira

import re
import requests
from datetime import datetime
from config import JIRA_USER
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
        match = re.search(pattern, comment, re.IGNORECASE)
        if match:
            fields[field] = match.group(1).strip()
   # Nếu bạn cần summary/description từ comment, gán lại đúng biến
    fields['summary'] = comment[:100]  # lấy 100 ký tự đầu làm summary
    fields['description'] = comment
    # Fallbacks an toàn
    fields.setdefault("assignee", JIRA_USER)
    fields.setdefault("epic_id", "EPIC-UNKNOWN")
    fields.setdefault("due_date", datetime.now().strftime("%Y-%m-%d"))
    fields.setdefault("expected", "Không có mô tả kết quả dự kiến")
    fields.setdefault("start_date", datetime.now().strftime("%Y-%m-%d"))

    # Dùng cho summary & description
    fields["description"] = f"""
    *TestCase Comment:*<br/>{comment}<br/><br/>
    *Mô tả lỗi:* {fields.get("expected")}<br/>
    *Ngày bắt đầu:* {fields.get("start_date")}<br/>
    """

    return fields

def create_jira_bug(case_id, notes, fields):
    print(f"Debug: case_id={case_id}, notes={notes}, fields={fields}")
    print(f"Debug: JIRA_URL={JIRA_URL}, JIRA_USER={JIRA_USER}, JIRA_PROJECT_KEY={JIRA_PROJECT_KEY}")
    if not fields.get("summary") or not fields.get("description"):
        print(f"❌ Thiếu summary hoặc description. Bỏ qua TestCase #{case_id}")
        return
    bug_data = {
        "fields": {
            "project": {"key": JIRA_PROJECT_KEY},
            "summary": f"[AUTO][TC#{case_id}] {fields['expected'][:80]}",
            "description": fields["description"],
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
  
    if response.status_code == 201:
        print(f"✅ Bug tạo thành công: {response.json().get('key')}")
    elif response.status_code == 400:
        print("⚠️ Lỗi 400 - Kiểm tra trường dữ liệu không hợp lệ.")
    elif response.status_code == 401:
        print("🔒 Lỗi 401 - Sai username/password Jira.")
    elif response.status_code == 403:
        print("🚫 Lỗi 403 - Không đủ quyền tạo bug.")
    else:
        print(f"❌ Tạo bug thất bại: {response.status_code} - {response.text}")
