# ~/Ubun_nitrate/import-script/test_login.py
from nitrate_utils.nitrate_helper import check_login_nitrate
print(">>> Bắt đầu kiểm tra login vào Nitrate...")  # ✅ Kiểm tra chạy đến đâu
NITRATE_URL = "http://127.0.0.1:8000/xmlrpc/"
NITRATE_USER = "thuypt"
NITRATE_PASS = "123456"

check_login_nitrate(NITRATE_URL, NITRATE_USER, NITRATE_PASS)
