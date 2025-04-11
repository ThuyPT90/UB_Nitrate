#!/bin/bash

# Đi vào thư mục dự án
cd ~/Ubun_nitrate/backend/Nitrate

# Kích hoạt môi trường ảo
# Kích hoạt venv (nếu tồn tại)
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "❌ Không tìm thấy môi trường ảo venv/. Hãy tạo bằng: python3 -m venv venv"
    exit 1
fi

# Thiết lập biến môi trường cho PostgreSQL
export NITRATE_DB_ENGINE=pgsql
export NITRATE_DB_NAME=nitrate
export NITRATE_DB_USER=nitrate
export NITRATE_DB_PASSWORD=nitrate
export NITRATE_DB_HOST=localhost
export NITRATE_DB_PORT=5432

# Khởi động PostgreSQL (nếu chưa chạy)
sudo service postgresql start

# Chạy server Nitrate
#python3 src/manage.py runserver
venv/bin/python src/manage.py runserver
