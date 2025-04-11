# nitrate_to_jira_bug.py
import os
print("🧩 Đang chạy từ:", os.getcwd())
print("📄 Danh sách file trong thư mục:")
print(os.listdir('.'))

from nitrate_helper import get_latest_run_with_failed_cases, get_executions_by_status
from jira_helper import create_jira_bug, parse_jira_fields_from_comment

# 🧩 Chọn các trạng thái test case sẽ tạo bug Jira
target_statuses = ["FAILED", "BLOCKED"]  # bạn có thể thêm: "IDLE", "ERROR", ...
print("📌 Đang lấy test run mới nhất có test case ở trạng thái:", target_statuses)

TEST_RUN_ID = get_latest_run_with_failed_cases(statuses=target_statuses)
if not TEST_RUN_ID:
    exit("Không tìm thấy Test Run phù hợp!")

executions = get_executions_by_status(run_id, statuses=target_statuses)
# 🐞 Gửi từng execution lên Jira
for exe in executions:
    case_id = exe['case_id']
    notes = exe.get('notes', '').strip()
    if not notes:
        print(f"⚠ Case #{case_id} không có notes. Bỏ qua.")
        continue

    print(f"\n🔍 TestCase #{case_id} (status: {exe['status']})\n{notes}")
    fields = parse_jira_fields_from_comment(notes)
    create_jira_bug(case_id, notes, fields)
