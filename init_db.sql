-- 创建数据库
CREATE DATABASE IF NOT EXISTS vm_management DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE vm_management;

-- 1. 用户表（bcrypt加密存储密码，字段长度兼容标准哈希）
CREATE TABLE IF NOT EXISTS `users` (
  `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '用户ID',
  `username` VARCHAR(50) NOT NULL UNIQUE COMMENT '登录用户名',
  `password` VARCHAR(255) NOT NULL COMMENT 'bcrypt加密后的密码哈希（标准60字符）',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) COMMENT '用户登录表';

-- 2. 项目表
CREATE TABLE IF NOT EXISTS `projects` (
  `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '项目ID',
  `project_name` VARCHAR(100) NOT NULL UNIQUE COMMENT '项目名称',
  `description` VARCHAR(500) DEFAULT '' COMMENT '项目描述',
  `create_user_id` INT NOT NULL COMMENT '创建人ID',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  FOREIGN KEY (`create_user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) COMMENT '项目表';

-- 3. 项目成员表（项目级 RBAC）
CREATE TABLE IF NOT EXISTS `project_members` (
  `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '记录ID',
  `project_id` INT NOT NULL COMMENT '项目ID',
  `user_id` INT NOT NULL COMMENT '用户ID',
  `role` VARCHAR(20) NOT NULL COMMENT '角色: owner/member',
  `valid_until` DATETIME NULL COMMENT '有效期，NULL表示长期',
  `created_by` INT NOT NULL COMMENT '授权人',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  UNIQUE KEY `uniq_project_user` (`project_id`, `user_id`),
  FOREIGN KEY (`project_id`) REFERENCES `projects`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`created_by`) REFERENCES `users`(`id`) ON DELETE CASCADE
) COMMENT '项目成员与角色绑定';

-- 4. 虚拟机信息表（对称加密存储SSH密码密文）
CREATE TABLE IF NOT EXISTS `virtual_machines` (
  `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '虚拟机ID',
  `project_id` INT NOT NULL COMMENT '所属项目ID',
  `vm_name` VARCHAR(100) NOT NULL COMMENT '虚拟机名称',
  `environment` VARCHAR(20) DEFAULT 'prod' COMMENT '环境: prod/staging/dev',
  `owner_name` VARCHAR(50) DEFAULT '' COMMENT '负责人',
  `ip_address` VARCHAR(50) NOT NULL COMMENT '虚拟机IP地址',
  `ssh_port` INT DEFAULT 22 COMMENT 'SSH端口（默认22）',
  `ssh_user` VARCHAR(50) NOT NULL COMMENT 'SSH登录用户名',
  `ssh_password` VARCHAR(255) NOT NULL COMMENT 'Fernet加密后的SSH密码密文',
  `os_type` VARCHAR(20) COMMENT '操作系统类型（如Linux/Windows）',
  `cpu_cores` INT DEFAULT 2 COMMENT 'CPU核数',
  `memory_gb` INT DEFAULT 4 COMMENT '内存(GB)',
  `disk_gb` INT DEFAULT 50 COMMENT '磁盘(GB)',
  `power_state` VARCHAR(20) DEFAULT 'ONLINE' COMMENT '运行状态 ONLINE/OFFLINE',
  `offline_status` VARCHAR(30) DEFAULT 'ONLINE' COMMENT '下线状态机',
  `offline_check_result` VARCHAR(10) DEFAULT 'PASS' COMMENT '最近检查结果 PASS/WARN/BLOCK',
  `last_power_action_time` DATETIME NULL COMMENT '最近开关机时间',
  `expire_time` DATETIME NULL COMMENT '到期时间',

  `cpu_usage` DECIMAL(5,2) DEFAULT 0 COMMENT 'CPU利用率%',
  `memory_usage` DECIMAL(5,2) DEFAULT 0 COMMENT '内存利用率%',
  `disk_usage` DECIMAL(5,2) DEFAULT 0 COMMENT '磁盘利用率%',
  `network_usage` DECIMAL(5,2) DEFAULT 0 COMMENT '网络利用率%',
  `active_sessions` INT DEFAULT 0 COMMENT '活跃登录会话数',
  `public_ports` VARCHAR(255) DEFAULT '' COMMENT '对外监听端口，逗号分隔',
  `port_whitelist` VARCHAR(255) DEFAULT '22' COMMENT '端口白名单，逗号分隔',
  `has_shared_storage` TINYINT(1) DEFAULT 0 COMMENT '是否挂载共享存储',
  `backup_in_progress` TINYINT(1) DEFAULT 0 COMMENT '是否备份中',
  `critical_snapshot_pending` TINYINT(1) DEFAULT 0 COMMENT '关键快照是否未清理',
  `last_major_change_at` DATETIME NULL COMMENT '最近重大变更时间',
  `cmdb_dependency` TINYINT(1) DEFAULT 0 COMMENT '是否被CMDB依赖',
  `high_priority_alerts_7d` TINYINT(1) DEFAULT 0 COMMENT '7天内高优告警',

  `remark` VARCHAR(500) COMMENT '备注信息',
  `create_user_id` INT NOT NULL COMMENT '录入用户ID（关联users表）',
  `is_deleted` TINYINT(1) DEFAULT 0 COMMENT '逻辑删除标记',
  `deleted_at` DATETIME NULL COMMENT '删除时间',
  `deleted_by` INT NULL COMMENT '删除人',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '录入时间',
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  FOREIGN KEY (`project_id`) REFERENCES `projects`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`create_user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) COMMENT '虚拟机信息表';

-- 5. 申请审批任务（删除/下线）
CREATE TABLE IF NOT EXISTS `workflow_tasks` (
  `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '任务ID',
  `task_type` VARCHAR(20) NOT NULL COMMENT '任务类型 OFFLINE/DELETE',
  `vm_id` INT NOT NULL COMMENT '虚拟机ID',
  `project_id` INT NOT NULL COMMENT '项目ID',
  `state` VARCHAR(30) NOT NULL COMMENT '任务状态机',
  `request_user_id` INT NOT NULL COMMENT '发起人ID',
  `request_role` VARCHAR(20) NOT NULL COMMENT '发起人项目角色',
  `check_result` VARCHAR(10) NOT NULL COMMENT '检查结果 PASS/WARN/BLOCK',
  `check_payload` JSON NULL COMMENT '检查详情',
  `manual_confirm_payload` JSON NULL COMMENT 'L3人工确认项',
  `force_reason` VARCHAR(500) DEFAULT '' COMMENT '强制下线原因',
  `risk_ack` VARCHAR(500) DEFAULT '' COMMENT '风险确认',
  `rollback_plan` VARCHAR(1000) DEFAULT '' COMMENT '回滚预案',
  `is_forced` TINYINT(1) DEFAULT 0 COMMENT '是否强制下线',
  `approval_user_id` INT NULL COMMENT '审批人ID',
  `approval_time` DATETIME NULL COMMENT '审批时间',
  `approval_comment` VARCHAR(500) DEFAULT '' COMMENT '审批意见',
  `execute_user_id` INT NULL COMMENT '执行人ID',
  `execute_time` DATETIME NULL COMMENT '执行时间',
  `operation_type` VARCHAR(30) DEFAULT '' COMMENT '最近动作类型',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  FOREIGN KEY (`vm_id`) REFERENCES `virtual_machines`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`project_id`) REFERENCES `projects`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`request_user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) COMMENT '删除/下线申请审批流程表';

-- 初始化管理员用户（先不插入，部署时通过代码生成正确哈希后手动插入）
-- 执行完SQL后，运行后端生成哈希再执行：INSERT INTO users (username, password) VALUES ('admin', '生成的标准哈希');
