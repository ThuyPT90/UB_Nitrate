import os, sys
import xml.etree.ElementTree as ET
# Thêm đường dẫn chứa thư viện nitrate đã clone
sys.path.insert(0, os.path.abspath("~/projects/Ubun_nitrate/import-script/Python-Nitrate/nitrate"))

from nitrate.xmlrpc import NitrateConnection

# Kết nối Nitrate server
conn = NitrateConnection.from_config()
print(conn.system.listMethods())
# Đường dẫn tới file XML
xml_file = "../test-data/tcms-testcases-2025-04-07.xml"

# Parse XML
tree = ET.parse(xml_file)
root = tree.getroot()

# Duyệt từng <testcase>
for tc in root.findall("testcase"):
    summary = tc.findtext("summary", default="(Không có tiêu đề)")
    actions = tc.findtext("action", default="(Không có bước thực hiện)")
    expected = tc.findtext("expectedresults", default="(Không có kết quả kỳ vọng)")
    plan_raw = tc.findtext("testplan_reference", default="1").strip()
    plan_id = int(plan_raw) if plan_raw.isdigit() else 1

    result = conn.TestCase().create({
        "summary": summary.strip(),
        "actions": actions.strip(),
        "expected": expected.strip(),
        "plan": plan_id,
    })

    print("✅ Đã tạo Test Case ID:", result["case_id"])
