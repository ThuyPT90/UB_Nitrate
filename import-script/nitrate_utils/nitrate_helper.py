# ~/Ubun_nitrate/import-script/nitrate_utils/nitrate_helper.py
import xmlrpc.client
print(">>> [nitrate_helper.py] File đã được import")  # ✅
def check_login_nitrate(url, username, password):
    try:
        server = xmlrpc.client.ServerProxy(url)
        response = server.Auth.login({
            "username": username,
            "password": password
        })

        if "id" in response:
            print("✅ Đăng nhập thành công!")
            print("Thông tin user:", response)
            return True
        else:
            print("❌ Đăng nhập thất bại. Không có user ID.")
            return False

    except Exception as e:
        print("❌ Lỗi kết nối hoặc đăng nhập:", str(e))
        return False
