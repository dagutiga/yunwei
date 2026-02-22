import io
import json
import os
import zipfile
from datetime import datetime, timedelta
from typing import Optional

import pymysql
from dotenv import load_dotenv
from fastapi import Body, Depends, FastAPI, Header, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from core.auth import encrypt_password, verify_password
from core.db import get_db_connection
from core.logger import log
from core.secret import SecretError, decrypt_secret, encrypt_secret
from core.ssh_client import SSHClient

load_dotenv()

app = FastAPI(title="虚拟机管理系统API", version="1.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class UserLogin(BaseModel):
    username: str
    password: str


class VMInfo(BaseModel):
    project_id: int
    vm_name: str
    ip_address: str
    ssh_port: int = 22
    ssh_user: str
    ssh_password: str
    os_type: str = ""
    environment: str = "prod"
    owner_name: str = ""
    cpu_cores: int = 2
    memory_gb: int = 4
    disk_gb: int = 50
    remark: str = ""


class SSHCommand(BaseModel):
    vm_id: int
    command: str


class ProjectCreate(BaseModel):
    project_name: str
    description: str = ""


class ProjectMemberUpsert(BaseModel):
    project_id: int
    username: str
    role: str = Field(pattern="^(owner|member)$")
    valid_until: Optional[datetime] = None


class OfflineApplyRequest(BaseModel):
    vm_id: int
    force_offline: bool = False
    force_reason: str = ""
    risk_ack: str = ""
    rollback_plan: str = ""
    data_migrated: bool = False
    dependency_cleared: bool = False
    stakeholders_notified: bool = False


class DeleteApplyRequest(BaseModel):
    vm_id: int
    confirm_text: str
    reason: str = ""


class TaskApproveRequest(BaseModel):
    action: str = Field(pattern="^(approve|reject)$")
    comment: str = ""


class UserCreateRequest(BaseModel):
    username: str
    password: str


class UserPasswordResetRequest(BaseModel):
    username: str
    new_password: str


current_users = {}


def ensure_default_admin() -> None:
    """自动补齐默认管理员，避免初始化阶段无法登录。"""
    default_password = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")
    if not default_password:
        return

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE username=%s", ("admin",))
            existing = cursor.fetchone()
            if existing:
                return

            cursor.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s)",
                ("admin", encrypt_password(default_password)),
            )
            conn.commit()
            log.info("检测到 admin 不存在，已自动创建默认管理员账号")
    except Exception as exc:
        if conn:
            conn.rollback()
        log.error(f"自动创建默认管理员失败: {exc}")
    finally:
        if conn:
            conn.close()


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def is_admin(user: dict) -> bool:
    return user.get("username") == "admin"


def parse_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", ""))
        except ValueError:
            return None
    return None


def parse_ports(value: str):
    if not value:
        return set()
    return {item.strip() for item in value.split(",") if item.strip()}


def ensure_project_permission(cursor, user: dict, project_id: int, action: str):
    if is_admin(user):
        return "admin"

    cursor.execute(
        """
        SELECT role, valid_until
        FROM project_members
        WHERE project_id=%s AND user_id=%s
        """,
        (project_id, user["id"]),
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=403, detail="PERMISSION_DENIED")

    valid_until = row.get("valid_until") if isinstance(row, dict) else row[1]
    if valid_until and valid_until < datetime.now():
        raise HTTPException(status_code=403, detail="PERMISSION_DENIED")

    role = row.get("role") if isinstance(row, dict) else row[0]
    permissions = {
        "owner": {"view", "initiate", "approve", "export", "manage_member"},
        "member": {"view", "initiate"},
    }
    if action not in permissions.get(role, set()):
        raise HTTPException(status_code=403, detail="PERMISSION_DENIED")
    return role


def check_vm_offline(vm: dict):
    threshold = float(os.getenv("OFFLINE_USAGE_THRESHOLD", "80"))
    l1 = []
    l2 = []
    l3 = [
        {"key": "data_migrated", "title": "数据已迁移/备份", "required": True},
        {"key": "dependency_cleared", "title": "上下游依赖已解除", "required": True},
        {"key": "stakeholders_notified", "title": "干系人已通知", "required": True},
    ]

    if vm["power_state"] != "OFFLINE":
        l1.append(
            {
                "rule": "L1_POWER_STATE",
                "title": "实例非关机",
                "evidence": f"当前状态={vm['power_state']}",
                "suggestion": "请先关机后再发起下线",
            }
        )

    usage_items = [
        ("CPU", float(vm["cpu_usage"] or 0)),
        ("内存", float(vm["memory_usage"] or 0)),
        ("磁盘", float(vm["disk_usage"] or 0)),
        ("网络", float(vm["network_usage"] or 0)),
    ]
    high_usage = [f"{name}:{value}%" for name, value in usage_items if value > threshold]
    if high_usage:
        l1.append(
            {
                "rule": "L1_HIGH_USAGE",
                "title": "资源使用率超过阈值",
                "evidence": ", ".join(high_usage),
                "suggestion": "请确认业务低峰后再执行",
            }
        )

    if int(vm["active_sessions"] or 0) > 0:
        l1.append(
            {
                "rule": "L1_ACTIVE_SESSIONS",
                "title": "存在活跃登录会话",
                "evidence": f"active_sessions={vm['active_sessions']}",
                "suggestion": "请通知在线用户并清理会话",
            }
        )

    public_ports = parse_ports(vm["public_ports"] or "")
    whitelist_ports = parse_ports(vm["port_whitelist"] or "")
    risky_ports = sorted(public_ports - whitelist_ports)
    if risky_ports:
        l1.append(
            {
                "rule": "L1_PUBLIC_PORTS",
                "title": "存在对外监听端口",
                "evidence": ",".join(risky_ports),
                "suggestion": "请下线前关闭对外端口或加入白名单审批",
            }
        )

    if int(vm["has_shared_storage"] or 0) == 1:
        l1.append(
            {
                "rule": "L1_SHARED_STORAGE",
                "title": "存在共享存储挂载",
                "evidence": "has_shared_storage=1",
                "suggestion": "请先卸载共享存储",
            }
        )
    if int(vm["backup_in_progress"] or 0) == 1:
        l1.append(
            {
                "rule": "L1_BACKUP_RUNNING",
                "title": "存在备份任务进行中",
                "evidence": "backup_in_progress=1",
                "suggestion": "请等待备份完成",
            }
        )
    if int(vm["critical_snapshot_pending"] or 0) == 1:
        l1.append(
            {
                "rule": "L1_SNAPSHOT_PENDING",
                "title": "关键快照未清理",
                "evidence": "critical_snapshot_pending=1",
                "suggestion": "请处理快照后重试",
            }
        )

    last_major_change_at = parse_datetime(vm["last_major_change_at"])
    if last_major_change_at and last_major_change_at >= datetime.now() - timedelta(days=7):
        l2.append(
            {
                "rule": "L2_RECENT_MAJOR_CHANGE",
                "title": "7天内重大变更",
                "evidence": f"last_major_change_at={last_major_change_at}",
                "suggestion": "建议观察变更稳定性后下线",
            }
        )

    if int(vm["cmdb_dependency"] or 0) == 1:
        l2.append(
            {
                "rule": "L2_CMDB_DEPENDENCY",
                "title": "被CMDB标记依赖",
                "evidence": "cmdb_dependency=1",
                "suggestion": "请先解除配置依赖",
            }
        )

    if int(vm["high_priority_alerts_7d"] or 0) == 1:
        l2.append(
            {
                "rule": "L2_HIGH_ALERT_7D",
                "title": "近7天高优告警",
                "evidence": "high_priority_alerts_7d=1",
                "suggestion": "请确认告警已处置",
            }
        )

    result = "PASS"
    if l1:
        result = "BLOCK"
    elif l2:
        result = "WARN"

    return {
        "result": result,
        "l1": l1,
        "l2": l2,
        "l3": l3,
        "summary": {
            "l1_count": len(l1),
            "l2_count": len(l2),
            "l3_required_count": len(l3),
        },
    }


def to_excel_xml_escape(value) -> str:
    text = "" if value is None else str(value)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def build_xlsx(headers, rows) -> bytes:
    sheet_rows = []
    sheet_rows.append(
        "<row>"
        + "".join(f"<c t=\"inlineStr\"><is><t>{to_excel_xml_escape(h)}</t></is></c>" for h in headers)
        + "</row>"
    )
    for row in rows:
        sheet_rows.append(
            "<row>"
            + "".join(
                f"<c t=\"inlineStr\"><is><t>{to_excel_xml_escape(v)}</t></is></c>" for v in row
            )
            + "</row>"
        )

    sheet_xml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<worksheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\">"
        "<sheetData>"
        + "".join(sheet_rows)
        + "</sheetData></worksheet>"
    )

    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>"""

    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""

    workbook = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="vm_export" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>"""

    workbook_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>"""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("xl/workbook.xml", workbook)
        zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return buffer.getvalue()


def get_current_user(
    authorization: Optional[str] = Header(default=None),
    x_token: Optional[str] = Header(default=None, alias="X-Token"),
    token: Optional[str] = Query(default=None),
):
    # 优先使用标准 Authorization: Bearer <token>
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    elif not token and x_token:
        token = x_token

    if token not in current_users:
        raise HTTPException(status_code=401, detail="未登录")
    user = current_users[token]
    user.setdefault("token", token)
    return user


@app.post("/api/login")
async def login(user: UserLogin):
    if user.username == "admin":
        ensure_default_admin()

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("SELECT id, username, password FROM users WHERE username=%s", (user.username,))
            db_user = cursor.fetchone()
            password_ok = bool(db_user) and verify_password(user.password, db_user["password"])
            # 兼容历史明文密码记录，登录成功后自动升级为 bcrypt 哈希。
            if db_user and not password_ok and db_user["password"] == user.password:
                cursor.execute(
                    "UPDATE users SET password=%s WHERE id=%s",
                    (encrypt_password(user.password), db_user["id"]),
                )
                conn.commit()
                password_ok = True

            if not db_user or not password_ok:
                raise HTTPException(status_code=401, detail="用户名或密码错误")

            token = f"token_{db_user['id']}_{os.urandom(8).hex()}"
            user_role = "admin" if db_user["username"] == "admin" else "user"
            current_users[token] = {
                "id": db_user["id"],
                "username": db_user["username"],
                "role": user_role,
                "token": token,
            }
            return {
                "code": 200,
                "message": "登录成功",
                "data": {
                    "token": token,
                    "user": {
                        "id": db_user["id"],
                        "username": db_user["username"],
                        "role": user_role,
                    },
                },
            }
    finally:
        if conn:
            conn.close()


@app.post("/api/logout")
async def logout(user: dict = Depends(get_current_user)):
    token = user.get("token")
    if token in current_users:
        del current_users[token]
    return {"code": 200, "message": "退出成功"}


@app.get("/api/projects")
async def list_projects(user: dict = Depends(get_current_user)):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            if is_admin(user):
                cursor.execute("SELECT id, project_name, description FROM projects ORDER BY id DESC")
            else:
                cursor.execute(
                    """
                    SELECT p.id, p.project_name, p.description, pm.role
                    FROM project_members pm
                    JOIN projects p ON p.id = pm.project_id
                    WHERE pm.user_id=%s AND (pm.valid_until IS NULL OR pm.valid_until >= NOW())
                    ORDER BY p.id DESC
                    """,
                    (user["id"],),
                )
            rows = cursor.fetchall()
        return {"code": 200, "message": "查询成功", "data": rows}
    finally:
        if conn:
            conn.close()


@app.post("/api/projects")
async def create_project(payload: ProjectCreate, user: dict = Depends(get_current_user)):
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="PERMISSION_DENIED")
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO projects (project_name, description, create_user_id) VALUES (%s, %s, %s)",
                (payload.project_name, payload.description, user["id"]),
            )
            project_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO project_members (project_id, user_id, role, created_by) VALUES (%s, %s, %s, %s)",
                (project_id, user["id"], "owner", user["id"]),
            )
            conn.commit()
        return {"code": 200, "message": "创建成功", "data": {"project_id": project_id}}
    except Exception as exc:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if conn:
            conn.close()


@app.post("/api/projects/member/upsert")
async def upsert_project_member(payload: ProjectMemberUpsert, user: dict = Depends(get_current_user)):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            ensure_project_permission(cursor, user, payload.project_id, "manage_member")
            cursor.execute("SELECT id FROM users WHERE username=%s", (payload.username,))
            target = cursor.fetchone()
            if not target:
                raise HTTPException(status_code=404, detail="用户不存在")

            cursor.execute(
                """
                INSERT INTO project_members (project_id, user_id, role, valid_until, created_by)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE role=VALUES(role), valid_until=VALUES(valid_until), created_by=VALUES(created_by)
                """,
                (payload.project_id, target[0], payload.role, payload.valid_until, user["id"]),
            )
            conn.commit()
        return {"code": 200, "message": "成员配置成功"}
    except HTTPException:
        raise
    except Exception as exc:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if conn:
            conn.close()


@app.get("/api/users")
async def list_users(user: dict = Depends(get_current_user)):
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="PERMISSION_DENIED")

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("SELECT id, username, create_time FROM users ORDER BY id DESC")
            rows = cursor.fetchall()
        return {"code": 200, "message": "查询成功", "data": rows}
    finally:
        if conn:
            conn.close()


@app.post("/api/users")
async def create_user(payload: UserCreateRequest, user: dict = Depends(get_current_user)):
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="PERMISSION_DENIED")
    if payload.username.lower() == "admin":
        raise HTTPException(status_code=400, detail="不能创建保留用户名")
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="密码至少 6 位")

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE username=%s", (payload.username,))
            if cursor.fetchone():
                raise HTTPException(status_code=409, detail="用户名已存在")

            cursor.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s)",
                (payload.username, encrypt_password(payload.password)),
            )
            user_id = cursor.lastrowid
            conn.commit()
        return {"code": 200, "message": "创建用户成功", "data": {"user_id": user_id}}
    finally:
        if conn:
            conn.close()


@app.post("/api/users/password/reset")
async def reset_user_password(payload: UserPasswordResetRequest, user: dict = Depends(get_current_user)):
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="PERMISSION_DENIED")
    if payload.username.lower() == "admin":
        raise HTTPException(status_code=400, detail="请勿通过此接口重置 admin")
    if len(payload.new_password) < 6:
        raise HTTPException(status_code=400, detail="密码至少 6 位")

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE username=%s", (payload.username,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="用户不存在")

            cursor.execute(
                "UPDATE users SET password=%s WHERE username=%s",
                (encrypt_password(payload.new_password), payload.username),
            )
            conn.commit()
        return {"code": 200, "message": "密码重置成功"}
    finally:
        if conn:
            conn.close()


@app.post("/api/vm/add")
async def add_vm(vm: VMInfo, user: dict = Depends(get_current_user)):
    conn = None
    try:
        conn = get_db_connection()
        encrypted_pwd = encrypt_secret(vm.ssh_password)
        with conn.cursor() as cursor:
            ensure_project_permission(cursor, user, vm.project_id, "initiate")
            cursor.execute(
                """
                INSERT INTO virtual_machines
                (project_id, vm_name, ip_address, ssh_port, ssh_user, ssh_password, os_type, environment,
                 owner_name, cpu_cores, memory_gb, disk_gb, remark, create_user_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    vm.project_id,
                    vm.vm_name,
                    vm.ip_address,
                    vm.ssh_port,
                    vm.ssh_user,
                    encrypted_pwd,
                    vm.os_type,
                    vm.environment,
                    vm.owner_name,
                    vm.cpu_cores,
                    vm.memory_gb,
                    vm.disk_gb,
                    vm.remark,
                    user["id"],
                ),
            )
            vm_id = cursor.lastrowid
            conn.commit()
        return {"code": 200, "message": "录入成功", "data": {"vm_id": vm_id}}
    except HTTPException:
        raise
    except Exception as exc:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"录入失败: {exc}")
    finally:
        if conn:
            conn.close()


@app.get("/api/vm/list")
async def list_vm(
    project_id: Optional[int] = Query(default=None),
    keyword: Optional[str] = Query(default=""),
    user: dict = Depends(get_current_user),
):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            params = []
            sql = """
                SELECT vm.id, vm.project_id, p.project_name, vm.vm_name, vm.ip_address, vm.environment,
                       vm.owner_name, vm.ssh_port, vm.ssh_user, vm.os_type, vm.cpu_cores, vm.memory_gb,
                       vm.disk_gb, vm.power_state, vm.offline_status, vm.offline_check_result,
                       vm.last_power_action_time, vm.remark, vm.create_time
                FROM virtual_machines vm
                JOIN projects p ON p.id = vm.project_id
                WHERE vm.is_deleted=0
            """
            if is_admin(user):
                if project_id:
                    sql += " AND vm.project_id=%s"
                    params.append(project_id)
            else:
                sql += " AND vm.project_id IN (SELECT project_id FROM project_members WHERE user_id=%s AND (valid_until IS NULL OR valid_until >= NOW()))"
                params.append(user["id"])
                if project_id:
                    sql += " AND vm.project_id=%s"
                    params.append(project_id)

            if keyword:
                sql += " AND (vm.vm_name LIKE %s OR vm.ip_address LIKE %s OR p.project_name LIKE %s)"
                fuzzy = f"%{keyword}%"
                params.extend([fuzzy, fuzzy, fuzzy])

            sql += " ORDER BY vm.id DESC"
            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()
        return {"code": 200, "message": "查询成功", "data": rows}
    finally:
        if conn:
            conn.close()


@app.post("/api/vm/ssh/exec")
async def ssh_exec(cmd: SSHCommand, user: dict = Depends(get_current_user)):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                """
                SELECT id, project_id, ip_address, ssh_port, ssh_user, ssh_password
                FROM virtual_machines
                WHERE id=%s AND is_deleted=0
                """,
                (cmd.vm_id,),
            )
            vm = cursor.fetchone()
            if not vm:
                raise HTTPException(status_code=404, detail="虚拟机不存在")
            ensure_project_permission(cursor, user, vm["project_id"], "view")

        try:
            plain_ssh_password = decrypt_secret(vm["ssh_password"])
        except SecretError:
            if isinstance(vm.get("ssh_password"), str) and vm["ssh_password"].startswith("$2"):
                raise HTTPException(status_code=400, detail="该虚拟机凭据为旧版不可解密数据，请重新录入SSH密码")
            raise HTTPException(status_code=500, detail="虚拟机凭据解密失败，请联系管理员")

        ssh_client = SSHClient(
            ip=vm["ip_address"],
            port=vm["ssh_port"],
            username=vm["ssh_user"],
            password=plain_ssh_password,
        )
        stdout, stderr = ssh_client.execute_command(cmd.command)
        ssh_client.close()
        return {"code": 200, "message": "执行成功", "data": {"stdout": stdout, "stderr": stderr}}
    except HTTPException:
        raise
    except Exception as exc:
        log.error(f"SSH执行命令失败: {exc}")
        raise HTTPException(status_code=500, detail=f"执行失败: {exc}")
    finally:
        if conn:
            conn.close()


@app.post("/api/vm/offline/check")
async def offline_check(vm_id: int = Body(embed=True), user: dict = Depends(get_current_user)):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("SELECT * FROM virtual_machines WHERE id=%s AND is_deleted=0", (vm_id,))
            vm = cursor.fetchone()
            if not vm:
                raise HTTPException(status_code=404, detail="虚拟机不存在")
            ensure_project_permission(cursor, user, vm["project_id"], "view")

            result = check_vm_offline(vm)
            cursor.execute(
                "UPDATE virtual_machines SET offline_check_result=%s WHERE id=%s",
                (result["result"], vm_id),
            )
            conn.commit()
        return {"code": 200, "message": "检查完成", "data": result}
    finally:
        if conn:
            conn.close()


@app.post("/api/vm/offline/apply")
async def offline_apply(payload: OfflineApplyRequest, user: dict = Depends(get_current_user)):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("SELECT * FROM virtual_machines WHERE id=%s AND is_deleted=0", (payload.vm_id,))
            vm = cursor.fetchone()
            if not vm:
                raise HTTPException(status_code=404, detail="虚拟机不存在")
            request_role = ensure_project_permission(cursor, user, vm["project_id"], "initiate")

            check_result = check_vm_offline(vm)
            if check_result["result"] == "BLOCK":
                raise HTTPException(status_code=400, detail="OFFLINE_CHECK_BLOCKED")

            manual_confirm = {
                "data_migrated": payload.data_migrated,
                "dependency_cleared": payload.dependency_cleared,
                "stakeholders_notified": payload.stakeholders_notified,
            }
            if not all(manual_confirm.values()):
                raise HTTPException(status_code=400, detail="APPROVAL_REQUIRED")

            if payload.force_offline:
                if request_role != "owner" and not is_admin(user):
                    raise HTTPException(status_code=403, detail="PERMISSION_DENIED")
                if not payload.force_reason or not payload.risk_ack or not payload.rollback_plan:
                    raise HTTPException(status_code=400, detail="APPROVAL_REQUIRED")

            state = "PENDING_OWNER_APPROVAL" if request_role == "member" else "PENDING_APPROVAL"
            cursor.execute(
                """
                INSERT INTO workflow_tasks
                (task_type, vm_id, project_id, state, request_user_id, request_role, check_result,
                 check_payload, manual_confirm_payload, force_reason, risk_ack, rollback_plan,
                 is_forced, operation_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    "OFFLINE",
                    payload.vm_id,
                    vm["project_id"],
                    state,
                    user["id"],
                    request_role,
                    check_result["result"],
                    json.dumps(check_result, ensure_ascii=False),
                    json.dumps(manual_confirm, ensure_ascii=False),
                    payload.force_reason,
                    payload.risk_ack,
                    payload.rollback_plan,
                    1 if payload.force_offline else 0,
                    "FORCED_OFFLINE" if payload.force_offline else "OFFLINE_APPLY",
                ),
            )
            task_id = cursor.lastrowid
            cursor.execute(
                "UPDATE virtual_machines SET offline_status=%s, offline_check_result=%s WHERE id=%s",
                ("OFFLINE_APPLYING", check_result["result"], payload.vm_id),
            )
            conn.commit()
        return {"code": 200, "message": "下线申请已提交", "data": {"task_id": task_id}}
    except HTTPException:
        raise
    except Exception as exc:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if conn:
            conn.close()


@app.post("/api/vm/delete/apply")
async def delete_apply(payload: DeleteApplyRequest, user: dict = Depends(get_current_user)):
    if payload.confirm_text != "DELETE":
        raise HTTPException(status_code=400, detail="请输入 DELETE 进行二次确认")
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("SELECT * FROM virtual_machines WHERE id=%s AND is_deleted=0", (payload.vm_id,))
            vm = cursor.fetchone()
            if not vm:
                raise HTTPException(status_code=404, detail="虚拟机不存在")
            request_role = ensure_project_permission(cursor, user, vm["project_id"], "initiate")

            check_result = check_vm_offline(vm)
            if check_result["result"] == "BLOCK":
                raise HTTPException(status_code=400, detail="OFFLINE_CHECK_BLOCKED")

            state = "PENDING_OWNER_APPROVAL" if request_role == "member" else "PENDING_APPROVAL"
            cursor.execute(
                """
                INSERT INTO workflow_tasks
                (task_type, vm_id, project_id, state, request_user_id, request_role, check_result,
                 check_payload, operation_type, approval_comment)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    "DELETE",
                    payload.vm_id,
                    vm["project_id"],
                    state,
                    user["id"],
                    request_role,
                    check_result["result"],
                    json.dumps(check_result, ensure_ascii=False),
                    "DELETE_APPLY",
                    payload.reason,
                ),
            )
            task_id = cursor.lastrowid
            conn.commit()
        return {"code": 200, "message": "删除申请已提交", "data": {"task_id": task_id}}
    finally:
        if conn:
            conn.close()


@app.get("/api/tasks/my")
async def my_tasks(user: dict = Depends(get_current_user)):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                """
                SELECT t.id, t.task_type, t.state, t.check_result, t.request_role, t.is_forced,
                       t.vm_id, vm.vm_name, p.project_name, t.create_time, t.approval_time, t.operation_type
                FROM workflow_tasks t
                JOIN virtual_machines vm ON vm.id=t.vm_id
                JOIN projects p ON p.id=t.project_id
                WHERE t.request_user_id=%s
                ORDER BY t.id DESC
                """,
                (user["id"],),
            )
            rows = cursor.fetchall()
        return {"code": 200, "message": "查询成功", "data": rows}
    finally:
        if conn:
            conn.close()


@app.get("/api/tasks/pending")
async def pending_tasks(user: dict = Depends(get_current_user)):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            if is_admin(user):
                cursor.execute(
                    """
                    SELECT t.id, t.task_type, t.state, t.request_role, t.vm_id, vm.vm_name,
                           p.project_name, u.username AS requester, t.create_time
                    FROM workflow_tasks t
                    JOIN virtual_machines vm ON vm.id=t.vm_id
                    JOIN projects p ON p.id=t.project_id
                    JOIN users u ON u.id=t.request_user_id
                    WHERE t.state IN ('PENDING_APPROVAL', 'PENDING_OWNER_APPROVAL')
                    ORDER BY t.id DESC
                    """
                )
            else:
                cursor.execute(
                    """
                    SELECT t.id, t.task_type, t.state, t.request_role, t.vm_id, vm.vm_name,
                           p.project_name, u.username AS requester, t.create_time
                    FROM workflow_tasks t
                    JOIN virtual_machines vm ON vm.id=t.vm_id
                    JOIN projects p ON p.id=t.project_id
                    JOIN users u ON u.id=t.request_user_id
                    JOIN project_members pm ON pm.project_id=t.project_id AND pm.user_id=%s
                    WHERE t.state='PENDING_OWNER_APPROVAL' AND pm.role='owner'
                    ORDER BY t.id DESC
                    """,
                    (user["id"],),
                )
            rows = cursor.fetchall()
        return {"code": 200, "message": "查询成功", "data": rows}
    finally:
        if conn:
            conn.close()


@app.post("/api/tasks/{task_id}/approve")
async def approve_task(task_id: int, payload: TaskApproveRequest, user: dict = Depends(get_current_user)):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                """
                SELECT t.*, vm.vm_name
                FROM workflow_tasks t
                JOIN virtual_machines vm ON vm.id=t.vm_id
                WHERE t.id=%s
                """,
                (task_id,),
            )
            task = cursor.fetchone()
            if not task:
                raise HTTPException(status_code=404, detail="任务不存在")

            is_owner = False
            if not is_admin(user):
                role = ensure_project_permission(cursor, user, task["project_id"], "approve")
                is_owner = role == "owner"

            if task["state"] not in ("PENDING_OWNER_APPROVAL", "PENDING_APPROVAL"):
                raise HTTPException(status_code=409, detail="VM_STATE_CONFLICT")

            if payload.action == "reject":
                cursor.execute(
                    """
                    UPDATE workflow_tasks
                    SET state='CANCELED', approval_user_id=%s, approval_time=NOW(), approval_comment=%s, operation_type='REJECTED'
                    WHERE id=%s
                    """,
                    (user["id"], payload.comment or "已驳回", task_id),
                )
                if task["task_type"] == "OFFLINE":
                    cursor.execute(
                        "UPDATE virtual_machines SET offline_status='ONLINE' WHERE id=%s",
                        (task["vm_id"],),
                    )
                conn.commit()
                return {"code": 200, "message": "已驳回"}

            if task["state"] == "PENDING_OWNER_APPROVAL":
                if not is_owner:
                    raise HTTPException(status_code=403, detail="PERMISSION_DENIED")
                cursor.execute(
                    """
                    UPDATE workflow_tasks
                    SET state='PENDING_APPROVAL', approval_user_id=%s, approval_time=NOW(),
                        approval_comment=%s, operation_type='OWNER_APPROVED'
                    WHERE id=%s
                    """,
                    (user["id"], payload.comment or "负责人审批通过", task_id),
                )
                if task["task_type"] == "OFFLINE":
                    cursor.execute("UPDATE virtual_machines SET offline_status='OFFLINE_REVIEW' WHERE id=%s", (task["vm_id"],))
                conn.commit()
                return {"code": 200, "message": "负责人审批通过，已提交管理员审批"}

            if not is_admin(user):
                raise HTTPException(status_code=403, detail="PERMISSION_DENIED")

            cursor.execute(
                """
                UPDATE workflow_tasks
                SET state='APPROVED', approval_user_id=%s, approval_time=NOW(), approval_comment=%s
                WHERE id=%s
                """,
                (user["id"], payload.comment or "管理员审批通过", task_id),
            )

            if task["task_type"] == "OFFLINE":
                cursor.execute(
                    """
                    UPDATE workflow_tasks
                    SET state='SUCCESS', execute_user_id=%s, execute_time=NOW(), operation_type='OFFLINE_EXECUTED'
                    WHERE id=%s
                    """,
                    (user["id"], task_id),
                )
                cursor.execute(
                    """
                    UPDATE virtual_machines
                    SET offline_status='OFFLINE_DONE', power_state='OFFLINE', last_power_action_time=NOW()
                    WHERE id=%s
                    """,
                    (task["vm_id"],),
                )
            else:
                cursor.execute(
                    """
                    UPDATE workflow_tasks
                    SET state='SUCCESS', execute_user_id=%s, execute_time=NOW(), operation_type='DELETE_EXECUTED'
                    WHERE id=%s
                    """,
                    (user["id"], task_id),
                )
                cursor.execute(
                    """
                    UPDATE virtual_machines
                    SET is_deleted=1, deleted_at=NOW(), deleted_by=%s
                    WHERE id=%s
                    """,
                    (user["id"], task["vm_id"]),
                )
            conn.commit()
            return {"code": 200, "message": "审批并执行完成"}
    except HTTPException:
        raise
    except Exception as exc:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if conn:
            conn.close()


@app.get("/api/vm/export")
async def export_vms(
    project_id: Optional[int] = Query(default=None),
    keyword: Optional[str] = Query(default=""),
    user: dict = Depends(get_current_user),
):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            params = []
            sql = """
                SELECT vm.id, vm.vm_name, p.project_name, vm.environment, vm.owner_name,
                       vm.create_time, vm.expire_time, vm.cpu_cores, vm.memory_gb, vm.disk_gb,
                       vm.ip_address, vm.os_type, vm.power_state, vm.last_power_action_time,
                       vm.offline_status, vm.offline_check_result,
                       req.username AS request_user, t.operation_type, approver.username AS approver,
                       t.approval_time
                FROM virtual_machines vm
                JOIN projects p ON p.id=vm.project_id
                LEFT JOIN workflow_tasks t ON t.vm_id=vm.id
                    AND t.id=(SELECT MAX(id) FROM workflow_tasks wt WHERE wt.vm_id=vm.id)
                LEFT JOIN users req ON req.id=t.request_user_id
                LEFT JOIN users approver ON approver.id=t.approval_user_id
                WHERE vm.is_deleted=0
            """

            if is_admin(user):
                if project_id:
                    sql += " AND vm.project_id=%s"
                    params.append(project_id)
            else:
                cursor.execute(
                    """
                    SELECT pm.role FROM project_members pm
                    WHERE pm.user_id=%s AND pm.project_id=%s AND (pm.valid_until IS NULL OR pm.valid_until >= NOW())
                    """,
                    (user["id"], project_id or 0),
                )
                role_row = cursor.fetchone()
                if project_id and role_row and role_row["role"] == "owner":
                    sql += " AND vm.project_id=%s"
                    params.append(project_id)
                else:
                    raise HTTPException(status_code=403, detail="PERMISSION_DENIED")

            if keyword:
                fuzzy = f"%{keyword}%"
                sql += " AND (vm.vm_name LIKE %s OR vm.ip_address LIKE %s OR p.project_name LIKE %s)"
                params.extend([fuzzy, fuzzy, fuzzy])

            sql += " ORDER BY vm.id DESC LIMIT 5000"
            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()

        headers = [
            "VM名称",
            "ID",
            "项目",
            "环境",
            "负责人",
            "创建时间",
            "到期时间",
            "CPU",
            "内存",
            "磁盘",
            "IP",
            "OS",
            "运行状态",
            "最近开关机时间",
            "下线状态",
            "检查结果",
            "最近操作人",
            "操作类型",
            "审批人",
            "审批时间",
        ]
        data_rows = [
            [
                row["vm_name"],
                row["id"],
                row["project_name"],
                row["environment"],
                row["owner_name"],
                row["create_time"],
                row["expire_time"],
                row["cpu_cores"],
                row["memory_gb"],
                row["disk_gb"],
                row["ip_address"],
                row["os_type"],
                row["power_state"],
                row["last_power_action_time"],
                row["offline_status"],
                row["offline_check_result"],
                row["request_user"],
                row["operation_type"],
                row["approver"],
                row["approval_time"],
            ]
            for row in rows
        ]
        xlsx_bytes = build_xlsx(headers, data_rows)
        return Response(
            content=xlsx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=vm_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            },
        )
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", 8000)),
        reload=True,
    )