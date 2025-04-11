from jira_helper import create_jira_bug, parse_jira_fields_from_comment

# 🔹 Giả lập dữ liệu giống như test case từ Nitrate
fake_notes = """
assignee: thuyPT3
epic_id: PAYT-001
due_date: 2025-04-15
expected: Hệ thống phải hiển thị lỗi khi user nhập sai mật khẩu
start_date: 2025-04-10
Bug mô tả lỗi: Khi user login sai mật khẩu thì không hiện thông báo lỗi mà reload lại trang.<br/>
""" 

fake_case_id = 9999

# 🔍 Parse thông tin từ notes
fields = parse_jira_fields_from_comment(fake_notes)

# 🚀 Gửi bug thật lên Jira
create_jira_bug(fake_case_id, fake_notes, fields)
