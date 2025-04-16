from django.apps import AppConfig

class TestCasesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tcms.testcases'

    def ready(self):
        print("✅ TestCases app đã khởi động – kích hoạt signals.")
        import tcms.plugins_support.signals  # Gọi signal khi app sẵn sàng
        import tcms.plugins_support.register_signal  # ✅ Import từ file mới
