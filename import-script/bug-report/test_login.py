from xmlrpc.client import ServerProxy

server = ServerProxy("http://127.0.0.1:8000/xmlrpc/")
session_id = server.Auth.login({"username": "thuypt", "password": "123456"})
print("Đăng nhập thành công, session ID:", session_id)
