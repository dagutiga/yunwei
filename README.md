# 云运维管理平台 (VM Management System)

## 项目概述

一个面向企业的虚拟机运维管理平台，支持多项目管理、虚拟机全生命周期管理（录入 -> 使用 -> 下线/删除审批）、Web 端 SSH 操作等功能。

## 技术栈

- **前端**: Vue 3 + Element Plus + Pinia + Xterm.js + Vite
- **后端**: FastAPI + Python 3.10 + Paramiko
- **数据库**: MySQL

## 核心功能

- 用户管理（注册、登录、密码重置）
- 项目管理（创建项目、添加项目成员）
- 虚拟机管理（录入、配置规格）
- SSH 远程执行
- 下线审批工作流
- 删除审批工作流
- 任务管理

## 安全特性

- SSH 密码 Fernet 对称加密
- 用户密码 bcrypt 加密
- 项目级 RBAC（owner/member 权限分离）
- 敏感操作审批工作流

## 项目结构

```
yunwei/
├── backend/           # 后端代码 (FastAPI)
│   ├── app.py         # 主应用
│   ├── core/          # 核心模块
│   │   ├── auth.py    # 认证/密码加密
│   │   ├── db.py      # 数据库连接
│   │   ├── ssh_client.py  # SSH客户端
│   │   └── secret.py  # 密码加密
│   └── requirements.txt
├── frontend/          # 前端代码 (Vue 3)
│   ├── src/
│   │   ├── views/     # 页面视图
│   │   ├── api/       # API 调用
│   │   ├── router/    # 路由
│   │   ├── store/     # 状态管理
│   │   └── components/# 组件
│   └── package.json
└── init_db.sql        # 数据库初始化脚本
```
