-- Jenkins CI/CD + Ansible 初始化：增量迁移脚本（MySQL 8.x）
-- 执行前建议：
-- 1) 先在测试库验证；2) 业务低峰执行；3) 全量备份。

USE vm_management;

START TRANSACTION;

-- 1) VM 表新增初始化状态字段
ALTER TABLE `virtual_machines`
  ADD COLUMN `init_status` VARCHAR(20) NOT NULL DEFAULT 'INIT_PENDING' COMMENT '初始化状态 INIT_PENDING/INIT_RUNNING/INIT_DONE/INIT_FAILED' AFTER `offline_check_result`,
  ADD COLUMN `init_last_job_id` BIGINT NULL COMMENT '最近一次初始化任务ID' AFTER `init_status`,
  ADD COLUMN `init_last_time` DATETIME NULL COMMENT '最近一次初始化完成时间' AFTER `init_last_job_id`,
  ADD COLUMN `init_last_error` VARCHAR(500) DEFAULT '' COMMENT '最近一次初始化失败原因' AFTER `init_last_time`;

ALTER TABLE `virtual_machines`
  ADD INDEX `idx_vm_init_status` (`init_status`),
  ADD INDEX `idx_vm_init_last_job` (`init_last_job_id`);

-- 2) Jenkins 连接配置（项目级）
CREATE TABLE IF NOT EXISTS `jenkins_configs` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '配置ID',
  `project_id` INT NOT NULL COMMENT '项目ID',
  `base_url` VARCHAR(255) NOT NULL COMMENT 'Jenkins地址',
  `username` VARCHAR(100) NOT NULL COMMENT 'Jenkins用户名',
  `token_cipher` VARCHAR(512) NOT NULL COMMENT 'API Token密文',
  `default_folder` VARCHAR(200) DEFAULT '' COMMENT '默认文件夹（可选）',
  `is_enabled` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否启用',
  `create_user_id` INT NOT NULL COMMENT '创建人',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  UNIQUE KEY `uniq_project_jenkins` (`project_id`),
  KEY `idx_jenkins_enabled` (`is_enabled`),
  CONSTRAINT `fk_jenkins_project` FOREIGN KEY (`project_id`) REFERENCES `projects`(`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_jenkins_user` FOREIGN KEY (`create_user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) COMMENT '项目级 Jenkins 配置';

-- 3) Jenkins Pipeline 清单（同步后本地缓存）
CREATE TABLE IF NOT EXISTS `jenkins_pipelines` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '流水线ID',
  `project_id` INT NOT NULL COMMENT '项目ID',
  `config_id` BIGINT NOT NULL COMMENT 'Jenkins配置ID',
  `pipeline_name` VARCHAR(150) NOT NULL COMMENT 'Jenkins job 名称（唯一键）',
  `display_name` VARCHAR(200) DEFAULT '' COMMENT '展示名称',
  `env_scope` VARCHAR(100) NOT NULL DEFAULT 'dev,staging,prod' COMMENT '允许环境，逗号分隔',
  `param_schema_json` JSON NULL COMMENT '参数模板定义JSON',
  `is_enabled` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否启用',
  `last_sync_time` DATETIME NULL COMMENT '最近同步时间',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  UNIQUE KEY `uniq_project_pipeline` (`project_id`, `pipeline_name`),
  KEY `idx_pipeline_enabled` (`project_id`, `is_enabled`),
  CONSTRAINT `fk_pipeline_project` FOREIGN KEY (`project_id`) REFERENCES `projects`(`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_pipeline_config` FOREIGN KEY (`config_id`) REFERENCES `jenkins_configs`(`id`) ON DELETE CASCADE
) COMMENT '项目 Jenkins Pipeline 列表';

-- 4) 部署任务（审批 + 执行状态）
CREATE TABLE IF NOT EXISTS `deploy_tasks` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '部署任务ID',
  `project_id` INT NOT NULL COMMENT '项目ID',
  `pipeline_id` BIGINT NOT NULL COMMENT '流水线ID',
  `target_env` VARCHAR(20) NOT NULL COMMENT '目标环境 dev/staging/prod',
  `params_json` JSON NULL COMMENT '触发参数快照',
  `change_log` VARCHAR(1000) DEFAULT '' COMMENT '变更说明',
  `state` VARCHAR(40) NOT NULL COMMENT '状态机',
  `request_user_id` INT NOT NULL COMMENT '发起人',
  `request_role` VARCHAR(20) NOT NULL COMMENT '发起人角色 owner/member/admin',
  `owner_approval_user_id` INT NULL COMMENT 'owner审批人',
  `owner_approval_time` DATETIME NULL COMMENT 'owner审批时间',
  `admin_approval_user_id` INT NULL COMMENT 'admin审批人',
  `admin_approval_time` DATETIME NULL COMMENT 'admin审批时间',
  `approval_comment` VARCHAR(500) DEFAULT '' COMMENT '审批意见',
  `jenkins_queue_id` VARCHAR(50) DEFAULT '' COMMENT 'Jenkins队列ID',
  `jenkins_build_number` INT NULL COMMENT 'Jenkins构建号',
  `jenkins_build_url` VARCHAR(500) DEFAULT '' COMMENT 'Jenkins构建URL',
  `result` VARCHAR(20) DEFAULT '' COMMENT '结果 SUCCESS/FAILED/CANCELED',
  `error_message` VARCHAR(1000) DEFAULT '' COMMENT '失败原因',
  `duration_sec` INT DEFAULT 0 COMMENT '执行耗时（秒）',
  `execute_start_time` DATETIME NULL COMMENT '执行开始时间',
  `execute_end_time` DATETIME NULL COMMENT '执行结束时间',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  KEY `idx_deploy_project_time` (`project_id`, `create_time`),
  KEY `idx_deploy_state` (`state`),
  KEY `idx_deploy_pipeline_env_state` (`pipeline_id`, `target_env`, `state`),
  CONSTRAINT `fk_deploy_project` FOREIGN KEY (`project_id`) REFERENCES `projects`(`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_deploy_pipeline` FOREIGN KEY (`pipeline_id`) REFERENCES `jenkins_pipelines`(`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_deploy_request_user` FOREIGN KEY (`request_user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) COMMENT '部署任务主表';

-- 5) Ansible 初始化任务
CREATE TABLE IF NOT EXISTS `vm_init_jobs` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '初始化任务ID',
  `vm_id` INT NOT NULL COMMENT '虚拟机ID',
  `project_id` INT NOT NULL COMMENT '项目ID',
  `state` VARCHAR(30) NOT NULL COMMENT '任务状态 INIT_RUNNING/INIT_DONE/INIT_FAILED/CANCELED',
  `ansible_playbook` VARCHAR(200) NOT NULL COMMENT '执行的Playbook名',
  `ansible_inventory` VARCHAR(200) DEFAULT '' COMMENT 'inventory来源标识',
  `request_user_id` INT NOT NULL COMMENT '发起人',
  `start_time` DATETIME NULL COMMENT '开始时间',
  `end_time` DATETIME NULL COMMENT '结束时间',
  `duration_sec` INT DEFAULT 0 COMMENT '耗时（秒）',
  `error_message` VARCHAR(1000) DEFAULT '' COMMENT '失败摘要',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  KEY `idx_init_vm_time` (`vm_id`, `create_time`),
  KEY `idx_init_state` (`state`),
  CONSTRAINT `fk_init_vm` FOREIGN KEY (`vm_id`) REFERENCES `virtual_machines`(`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_init_project` FOREIGN KEY (`project_id`) REFERENCES `projects`(`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_init_request_user` FOREIGN KEY (`request_user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) COMMENT 'VM 初始化任务';

-- 6) Ansible 初始化日志（可用于分页 + 流式增量）
CREATE TABLE IF NOT EXISTS `vm_init_logs` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '日志ID',
  `job_id` BIGINT NOT NULL COMMENT '初始化任务ID',
  `seq_no` INT NOT NULL COMMENT '顺序号（从1递增）',
  `step_key` VARCHAR(50) NOT NULL COMMENT '步骤标识，例如 JDK_INSTALL/APPUSER_CREATE',
  `log_level` VARCHAR(20) NOT NULL DEFAULT 'INFO' COMMENT 'INFO/WARN/ERROR',
  `message` TEXT NOT NULL COMMENT '日志内容',
  `raw_json` JSON NULL COMMENT '原始事件JSON',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  UNIQUE KEY `uniq_job_seq` (`job_id`, `seq_no`),
  KEY `idx_log_job_time` (`job_id`, `create_time`),
  CONSTRAINT `fk_init_log_job` FOREIGN KEY (`job_id`) REFERENCES `vm_init_jobs`(`id`) ON DELETE CASCADE
) COMMENT 'VM 初始化日志';

COMMIT;

-- 回滚提示（按需手动执行，勿直接生产运行）
-- DROP TABLE vm_init_logs;
-- DROP TABLE vm_init_jobs;
-- DROP TABLE deploy_tasks;
-- DROP TABLE jenkins_pipelines;
-- DROP TABLE jenkins_configs;
-- ALTER TABLE virtual_machines DROP COLUMN init_last_error, DROP COLUMN init_last_time, DROP COLUMN init_last_job_id, DROP COLUMN init_status;
