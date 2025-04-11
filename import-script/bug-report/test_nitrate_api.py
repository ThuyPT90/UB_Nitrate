from config import NITRATE_URL, NITRATE_USER, NITRATE_PASS
from tcms_api import TCMS

client = TCMS(url=NITRATE_URL, username=NITRATE_USER, password=NITRATE_PASS)

print("✅ Đang lấy test run mới nhất...")
latest_run = client.exec.TestRun.filter({'order_by': '-pk', 'limit': 1})
print(latest_run)
