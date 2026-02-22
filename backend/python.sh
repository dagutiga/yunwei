echo "=== 启动后端/重启 ==="
 pkill -f "python app.py"
nohup python app.py > backend.log 2>&1 &
