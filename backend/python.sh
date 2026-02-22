echo "=== 启动后端/重启 ==="
 pkill -f "python app.py"
nohup /app/yunwei/backend/.venv/bin/python /app/yunwei/backend/app.py > backend.log 2>&1 &
