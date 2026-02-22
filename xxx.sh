#!/bin/bash
# 部署脚本：deploy.sh
set -e

# 1. 初始化数据库
echo "=== 初始化数据库 ==="
# mysql -u root -p < init_db.sql

# 2. 部署后端
echo "=== 部署后端 ==="
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 生成admin用户密码哈希
echo "=== 生成admin密码哈希 ==="
HASH=$(python -c "from core.auth import encrypt_password; print(encrypt_password('admin123'))")
echo "生成的哈希: $HASH"

# 插入admin用户
mysql -h127.0.0.1 -uroot -p"P@ss1234" -e "USE vm_management; INSERT INTO users (username, password) VALUES ('admin', '$HASH'); COMMIT;"

# 启动后端
echo "=== 启动后端 ==="
nohup python app.py > backend.log 2>&1 &

# 3. 打包前端
echo "=== 打包前端 ==="
cd ../frontend
npm install
npm run build

# 4. 配置NGINX
echo "=== 配置NGINX ==="
sudo cp nginx.conf /etc/nginx/conf.d/vm-management.conf
sudo mv /etc/nginx/conf.d/default.conf /etc/nginx/conf.d/default.conf.bak
sudo nginx -t
sudo systemctl restart nginx

echo "=== 部署完成 ==="
echo "访问地址: http://127.0.0.1"
echo "默认账号: admin / admin123"
