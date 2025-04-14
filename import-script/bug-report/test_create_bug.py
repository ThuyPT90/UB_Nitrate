# test_create_bug.py

from jira_helper import parse_jira_fields_from_comment, create_jira_bug

# Đây là comment mô phỏng lấy từ testcase trong Nitrate
comment = """
assignee: thuypt3
epic_id: MP-123
due_date: 2025-04-20
expected: Hệ thống không hiển thị lỗi khi user nhập sai mật khẩu
start_date: 2025-04-19
Bug mô tả lỗi: Khi user nhập sai mật khẩu thì trang chỉ reload lại.
"""

case_id = 999  # Đây là ID giả lập test case để test thử
notes = comment  # Trong thực tế sẽ là notes từ testcase

# Parse các trường từ comment
fields = parse_jira_fields_from_comment(comment)

# Gọi hàm tạo Jira bug
create_jira_bug(case_id, notes, fields)
