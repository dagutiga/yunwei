import os
import pymysql
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Body, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from core.logger import log
from core.db import get_db_connection
from core.auth import verify_password
from core.secret import encrypt_secret, decrypt_secret, SecretError
from core.ssh_client import SSHClient

load_dotenv()

# 初始化FastAPI
app = FastAPI(title="虚拟机管理系统API", version="1.0")

# 跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据模型
class UserLogin(BaseModel):
    username: str
    password: str

class VMInfo(BaseModel):
    vm_name: str
    ip_address: str
    ssh_port: int = 22
    ssh_user: str
    ssh_password: str
    os_type: str = ""
    remark: str = ""

class SSHCommand(BaseModel):
    vm_id: int
    command: str

# 简易Token存储（生产环境用JWT）
current_users = {}

# 依赖：验证登录状态
def get_current_user(
    authorization: Optional[str] = Header(default=None),
    token: Optional[str] = Body(default=None, embed=True)
):
    # 优先使用 Authorization: Bearer <token>，兼容旧的 body token。
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()

    if token not in current_users:
        raise HTTPException(status_code=401, detail="未登录")
    user = current_users[token]
    if isinstance(user, dict):
        user.setdefault("token", token)
    return user

# 1. 登录接口（添加调试日志）
@app.post("/api/login")
async def login(user: UserLogin):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("SELECT id, username, password FROM users WHERE username=%s", (user.username,))
            db_user = cursor.fetchone()
            if not db_user:
                log.warning(f"用户 {user.username} 不存在")
                raise HTTPException(status_code=401, detail="用户名或密码错误")
            
            # 验证密码
            if not verify_password(user.password, db_user['password']):
                log.warning(f"用户 {user.username} 密码错误，哈希长度: {len(db_user['password'])}")
                raise HTTPException(status_code=401, detail="用户名或密码错误")
            
            # 生成Token
            token = f"token_{db_user['id']}_{os.urandom(8).hex()}"
            current_users[token] = {
                "id": db_user['id'],
                "username": db_user['username'],
                "token": token
            }
            
            log.info(f"用户 {user.username} 登录成功")
            return {
                "code": 200,
                "message": "登录成功",
                "data": {
                    "token": token,
                    "user": {"id": db_user['id'], "username": db_user['username']}
                }
            }
    finally:
        if conn:
            conn.close()

# 2. 退出登录
@app.post("/api/logout")
async def logout(user: dict = Depends(get_current_user)):
    token = user.get("token")
    if token in current_users:
        del current_users[token]
        log.info(f"用户退出登录: {token[:10]}****")
    return {
        "code": 200,
        "message": "退出成功"
    }

# 3. 录入虚拟机
@app.post("/api/vm/add")
async def add_vm(vm: VMInfo, user: dict = Depends(get_current_user)):
    conn = None
    try:
        conn = get_db_connection()
        encrypted_ssh_pwd = encrypt_secret(vm.ssh_password)
        
        with conn.cursor() as cursor:
            sql = """
            INSERT INTO virtual_machines 
            (vm_name, ip_address, ssh_port, ssh_user, ssh_password, os_type, remark, create_user_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                vm.vm_name, vm.ip_address, vm.ssh_port,
                vm.ssh_user, encrypted_ssh_pwd, vm.os_type,
                vm.remark, user['id']
            ))
            conn.commit()
        
        log.info(f"用户 {user['username']} 录入虚拟机 {vm.vm_name} 成功，ID: {cursor.lastrowid}")
        return {
            "code": 200,
            "message": "录入成功",
            "data": {"vm_id": cursor.lastrowid}
        }
    except Exception as e:
        if conn:
            conn.rollback()
        log.error(f"录入虚拟机失败: {e}")
        raise HTTPException(status_code=500, detail=f"录入失败: {str(e)}")
    finally:
        if conn:
            conn.close()

# 4. 获取虚拟机列表
@app.get("/api/vm/list")
async def list_vm(user: dict = Depends(get_current_user)):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("""
                SELECT id, vm_name, ip_address, ssh_port, ssh_user, os_type, remark 
                FROM virtual_machines WHERE create_user_id=%s
            """, (user['id'],))
            vms = cursor.fetchall()
        
        log.info(f"用户 {user['username']} 查询到 {len(vms)} 台虚拟机")
        return {
            "code": 200,
            "message": "查询成功",
            "data": vms
        }
    finally:
        if conn:
            conn.close()

# 5. SSH执行命令
@app.post("/api/vm/ssh/exec")
async def ssh_exec(cmd: SSHCommand, user: dict = Depends(get_current_user)):
    conn = None
    try:
        conn = get_db_connection()
        # 获取虚拟机信息
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("""
                SELECT ip_address, ssh_port, ssh_user, ssh_password 
                FROM virtual_machines WHERE id=%s AND create_user_id=%s
            """, (cmd.vm_id, user['id']))
            vm = cursor.fetchone()
            if not vm:
                log.warning(f"用户 {user['username']} 访问不存在的虚拟机ID: {cmd.vm_id}")
                raise HTTPException(status_code=404, detail="虚拟机不存在")
        
        try:
            plain_ssh_password = decrypt_secret(vm['ssh_password'])
        except SecretError:
            # 兼容历史错误数据（bcrypt 单向哈希），引导用户重新录入密码。
            if isinstance(vm.get('ssh_password'), str) and vm['ssh_password'].startswith("$2"):
                raise HTTPException(status_code=400, detail="该虚拟机凭据为旧版不可解密数据，请重新录入SSH密码")
            raise HTTPException(status_code=500, detail="虚拟机凭据解密失败，请联系管理员")

        ssh_client = SSHClient(
            ip=vm['ip_address'],
            port=vm['ssh_port'],
            username=vm['ssh_user'],
            password=plain_ssh_password
        )
        
        stdout, stderr = ssh_client.execute_command(cmd.command)
        ssh_client.close()
        
        return {
            "code": 200,
            "message": "执行成功",
            "data": {
                "stdout": stdout,
                "stderr": stderr
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"SSH执行命令失败: {e}")
        raise HTTPException(status_code=500, detail=f"执行失败: {str(e)}")
    finally:
        if conn:
            conn.close()

# 启动服务
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=os.getenv('API_HOST', '0.0.0.0'),
        port=int(os.getenv('API_PORT', 8000)),
        reload=True
    )
