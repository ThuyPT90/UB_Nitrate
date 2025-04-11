# nitrate_helper.py: Lấy test run và Testcase lỗi
import sys
sys.path.insert(0, '/home/thuypt90/Ubun_nitrate/tcms_api')
from tcms_api import TCMS
from config import NITRATE_URL, NITRATE_USER, NITRATE_PASS

client = TCMS(url=NITRATE_URL, username=NITRATE_USER, password=NITRATE_PASS).exec

def get_latest_run_with_failed_cases(statuses=["FAILED", "BLOCKED"], limit=10):
    
    all_runs = client.TestRun.filter({'order_by': '-pk', 'limit': limit})
    for run in all_runs:
        failed = client.TestCaseRun.filter({'run_id': run['id'], 'status__in': statuses}, uri=NITRATE_URL, username=NITRATE_USER, password=NITRATE_PASS)
        if failed:
            print(f"✔️ Found run #{run['id']} with {len(failed)} case(s) in {statuses}")
            return run['id']
    print("❌ No suitable test run found.")
    # Giả lập trả về một Test Run ID
    # return 12345
    return None

def get_executions_by_status(run_id, statuses=["FAILED", "BLOCKED"]):
    return client.TestExecution.filter({'run_id': run_id, 'status__in': statuses}, uri=NITRATE_URL, username=NITRATE_USER, password=NITRATE_PASS)
    # Giả lập trả về danh sách các case thất bại
    # return [
    #     {'case_id': 1, 'notes': 'Bug in feature X'},
    #     {'case_id': 2, 'notes': 'Bug in feature Y'}
    # ]