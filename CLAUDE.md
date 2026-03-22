# 云运维管理平台 (VM Management System)

## 项目概述

面向企业的虚拟机运维管理平台，支持多项目管理、虚拟机全生命周期管理（录入 -> 使用 -> 下线/删除审批）、Web 端 SSH 操作。

## 技术栈

- **前端**: Vue 3 + Element Plus + Pinia + Xterm.js + Vite
- **后端**: FastAPI + Python 3.10 + Paramiko
- **数据库**: MySQL

## 项目结构

```
yunwei/
├── backend/
│   ├── app.py                    # FastAPI 主应用，所有 API 路由在此
│   ├── core/
│   │   ├── auth.py               # 密码加密 (bcrypt)
│   │   ├── db.py                 # MySQL 数据库连接
│   │   ├── secret.py             # SSH 密码加密 (Fernet)
│   │   ├── ssh_client.py        # SSH 远程执行 (Paramiko)
│   │   └── logger.py             # 日志配置
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── views/
│   │   │   ├── LoginView.vue     # 登录页
│   │   │   └── MainView.vue      # 主页面
│   │   ├── components/
│   │   │   └── SSHTerminal.vue   # SSH 终端组件
│   │   ├── api/
│   │   │   ├── index.js          # Axios 配置
│   │   │   ├── user.js           # 用户 API
│   │   │   └── vm.js             # 虚拟机 API
│   │   ├── router/index.js       # Vue Router 配置
│   │   ├── store/user.js         # Pinia 用户状态
│   │   └── main.js               # 前端入口
│   └── package.json
└── init_db.sql                   # 数据库初始化脚本
```

## 核心功能

| 模块 | API 路由前缀 | 说明 |
|------|-------------|------|
| 用户管理 | `/api/user` | 注册、登录、密码重置 |
| 项目管理 | `/api/project` | 创建项目、添加成员 |
| 虚拟机 | `/api/vm` | 录入、查询、导出 |
| SSH | `/api/ssh` | 远程执行命令 |
| 审批 | `/api/approval` | 下线/删除审批工作流 |
| 任务 | `/api/task` | 我的任务、待审批列表 |

## 数据库表

- `users` - 用户表 (bcrypt 加密密码)
- `projects` - 项目表
- `project_members` - 项目成员 (owner/member 角色)
- `virtual_machines` - 虚拟机表 (Fernet 加密 SSH 密码)
- `offline_apply` - 下线申请
- `delete_apply` - 删除申请
- `approval_tasks` - 审批任务

## 关键实现细节

### 密码安全
- 用户密码: bcrypt 加密存储 (`core/auth.py`)
- SSH 密码: Fernet 对称加密存储 (`core/secret.py`)

### 权限控制
- 项目级 RBAC: owner (管理员) / member (成员)
- 敏感操作需审批: 下线、删除

### SSH 执行流程
1. 前端发送命令到后端 `/api/ssh/execute`
2. 后端从数据库解密 SSH 密码
3. 使用 Paramiko 连接到虚拟机执行命令
4. 返回执行结果到前端 Xterm.js 显示

## 运行方式

```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn app:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev
```

## 环境变量 (backend/.env)

```
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=xxx
DB_NAME=vm_management
SECRET_KEY=xxx  # Fernet 加密密钥
```
## 个人习惯
1. 全部用中文回复
2. 每次回复，结尾加个"喵~"


