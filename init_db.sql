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

-- 2. 虚拟机信息表（对称加密存储SSH密码密文）
CREATE TABLE IF NOT EXISTS `virtual_machines` (
  `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '虚拟机ID',
  `vm_name` VARCHAR(100) NOT NULL COMMENT '虚拟机名称',
  `ip_address` VARCHAR(50) NOT NULL COMMENT '虚拟机IP地址',
  `ssh_port` INT DEFAULT 22 COMMENT 'SSH端口（默认22）',
  `ssh_user` VARCHAR(50) NOT NULL COMMENT 'SSH登录用户名',
  `ssh_password` VARCHAR(255) NOT NULL COMMENT 'Fernet加密后的SSH密码密文',
  `os_type` VARCHAR(20) COMMENT '操作系统类型（如Linux/Windows）',
  `remark` VARCHAR(500) COMMENT '备注信息',
  `create_user_id` INT NOT NULL COMMENT '录入用户ID（关联users表）',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '录入时间',
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  FOREIGN KEY (`create_user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) COMMENT '虚拟机信息表';

-- 初始化管理员用户（先不插入，部署时通过代码生成正确哈希后手动插入）
-- 执行完SQL后，运行后端生成哈希再执行：INSERT INTO users (username, password) VALUES ('admin', '生成的标准哈希');
