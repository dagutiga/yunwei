## 1) 目标与范围
- 新增能力：
  - MySQL 逻辑备份（全库/按库/按表）
  - 备份恢复与跨环境迁移（源->目标）
  - 生产数据查询（受控 SQL）与轻量处理（受控 DML）
  - 生产查询结果导出（CSV/XLSX）
- 保持现有能力：VM管理、下线检查、删除审批、项目权限、审计导出
- 明确排除：重装功能（已移除）

## 2) 总体架构（集成现有后端）
- 后端新增模块（建议目录）
  - `backend/services/dbops/engine.py`：任务编排（提交/调度/状态机）
  - `backend/services/dbops/mysql_executor.py`：SQL执行、结果分页、超时控制
  - `backend/services/dbops/backup_runner.py`：mysqldump/xtrabackup封装（优先mysqldump）
  - `backend/services/dbops/migration_runner.py`：导入、校验、回滚策略
  - `backend/services/dbops/sanitizer.py`：SQL白名单/黑名单、脱敏规则
- 前端新增页面（挂在 MainView 的“数据库运维”分区）
  - 连接管理、备份中心、迁移中心、SQL工单、查询导出、审计日志
- 存储
  - 备份文件存放：`/data/backups/{project}/{date}/...`
  - 导出文件存放：`/data/exports/{project}/{date}/...`
  - 元数据与审计入库（见第4部分表结构）

## 3) 角色权限与审批策略（复用现有RBAC）
- 平台管理员（admin）
  - 全量：连接配置、备份/恢复/迁移审批与执行、生产查询审批、全量导出
- 项目负责人（owner）
  - 本项目：发起备份/迁移/查询处理工单、审批成员工单、本项目导出
- 项目成员（member）
  - 本项目：发起“只读查询工单”、查看结果；不可直接执行迁移和DML

审批分级（建议强制）
- L0（低风险）：`SELECT` + 行数限制 + 脱敏 => owner可批
- L1（中风险）：导出生产数据、大结果集、跨库查询 => owner + admin
- L2（高风险）：`UPDATE/DELETE/DDL`、恢复、迁移 => 必须 admin 最终审批

## 4) 数据库表设计（新增）
建议新增 5 张表（保持与你现有 `workflow_tasks` 风格一致）：

1. `db_connections`
- 字段：`id, project_id, name, env(prod/staging/dev), host, port, db_name, username, password_cipher, ssl_mode, readonly_flag, create_user_id, is_deleted, create_time`
- 说明：密码使用现有 `encrypt_secret/decrypt_secret`

2. `db_operation_tasks`
- 字段：`id, project_id, connection_id, task_type(BACKUP/RESTORE/MIGRATE/QUERY/DML/EXPORT), risk_level, state, request_user_id, approval_user_id, execute_user_id, sql_text, sql_fingerprint, params_json, result_meta_json, error_message, create_time, ...`
- 说明：统一任务中心，状态机与审批链路复用

3. `db_backups`
- 字段：`id, task_id, backup_type(FULL/SCHEMA/TABLE), storage_path, file_size, checksum, binlog_pos, expire_at, encrypted_flag, status`

4. `db_migrations`
- 字段：`id, task_id, source_conn_id, target_conn_id, object_scope_json, precheck_report_json, verify_report_json, rollback_ref`

5. `db_query_exports`
- 字段：`id, task_id, export_format(csv/xlsx), row_count, storage_path, masked_flag, download_token, token_expire_at`

## 5) 后端API设计（FastAPI）
前缀建议：`/api/dbops`

### 5.1 连接管理
- `POST /connections` 新建连接（admin/owner受控）
- `GET /connections` 列表（按项目过滤）
- `POST /connections/{id}/test` 连通性测试
- `DELETE /connections/{id}` 逻辑删除

### 5.2 备份
- `POST /backup/apply`
  - 入参：`project_id, connection_id, backup_type, scope, reason`
  - 返回：`task_id`
- `POST /backup/{task_id}/approve`
- `POST /backup/{task_id}/execute`
- `GET /backup/tasks` / `GET /backup/{task_id}`
- `GET /backup/files/{backup_id}/download`（短时token）

### 5.3 迁移/恢复
- `POST /migrate/apply`（源/目标连接、对象范围、是否结构+数据）
- `POST /restore/apply`（backup_id + target_conn_id）
- `POST /migrate/{task_id}/precheck`（字符集、版本、权限、磁盘空间）
- `POST /migrate/{task_id}/approve`、`POST /migrate/{task_id}/execute`

### 5.4 生产查询/处理
- `POST /sql/preview`
  - 做语法和风险扫描：类型识别（SELECT/DML/DDL）、影响行预估
- `POST /sql/apply`
  - 入参：`sql_text, params, reason, expected_rows`
- `POST /sql/{task_id}/approve`
- `POST /sql/{task_id}/execute`
- `GET /sql/{task_id}/result?page=1&page_size=100`

### 5.5 查询导出
- `POST /export/apply`（基于 task_id 或查询条件）
- `GET /export/{export_id}/download?token=...`
- `GET /export/tasks`

### 5.6 审计与可观测
- `GET /audit/logs`（按项目、用户、类型、时间筛选）
- `GET /metrics/overview`（成功率、平均耗时、失败原因TOP）

## 6) 任务状态机（统一）
`DRAFT -> PENDING_OWNER_APPROVAL -> PENDING_ADMIN_APPROVAL -> APPROVED -> RUNNING -> SUCCESS / FAILED / CANCELED`

- member发起：先到 owner
- owner发起低风险只读：可直接到 admin 或按策略直批
- 高风险（迁移/恢复/DML）：必须 admin 最终审批

## 7) 前端页面与交互（Vue + Element Plus）
在 `MainView.vue` 顶部新增一级功能入口：`数据库运维`

- 页面1：连接管理
  - 列表/新增/测试连接/启停（readonly标识）
- 页面2：备份中心
  - 发起备份、任务进度、备份包下载、到期策略
- 页面3：迁移中心
  - 发起迁移、预检查报告、审批流、执行日志、校验结果
- 页面4：SQL工单中心
  - SQL输入（只读/处理标签）-> 风险检测 -> 提交审批 -> 结果查看
- 页面5：查询导出中心
  - 导出申请、文件生成状态、token下载
- 页面6：数据库审计
  - 谁在什么时候执行了什么SQL、影响行数、审批链路

交互关键点
- 高风险操作二次确认（输入 `CONFIRM`）
- 显示“风险评级”与“阻断原因”
- 长任务用轮询或SSE刷新状态

## 8) 安全策略（重点）
- 权限隔离：严格项目级；连接不可跨项目使用
- 凭据安全：连接密码使用现有 `encrypt_secret` 存储；前端不回显明文
- SQL防护：
  - 默认仅允许 `SELECT`
  - `UPDATE/DELETE` 必须带 `WHERE` 且命中主键/索引条件（规则可配）
  - 禁止 `DROP DATABASE`、`TRUNCATE`（生产默认阻断）
- 结果保护：
  - 默认脱敏（手机号、身份证、邮箱、银行卡）
  - 导出行数上限（如 20万）+ 列白名单
  - 下载链接短时有效（如10分钟）+ 一次性token
- 审计合规：SQL原文+指纹+审批人+执行人+影响行数+来源IP 全量留痕
- 运行安全：执行超时（如60s）、并发限制、失败自动告警

## 9) 执行引擎建议
- 同步API + 异步任务执行（首版可用 `BackgroundTasks`，后续升级 Celery/RQ）
- 大任务（备份/迁移/导出）进入任务队列
- 失败重试：仅幂等任务重试（查询、导出）；迁移/恢复禁止自动重试

## 10) 与现有代码集成点
- 后端：在 `backend/app.py` 注册新路由（建议拆分 `routers/dbops.py`）
- 权限：复用 `ensure_project_permission`，新增动作：`db_view/db_query/db_export/db_approve/db_execute`
- 审批：可复用 `workflow_tasks` 思路，但建议数据库操作用独立 `db_operation_tasks`
- 前端：
  - 新增 API 文件：`frontend/src/api/dbops.js`
  - 新增视图：`frontend/src/views/dbops/*.vue`
  - 在 `MainView.vue` 增加入口Tab

## 11) 里程碑（两周可交付MVP）
- W1：表结构 + 后端连接管理/查询工单/审批 + 前端SQL工单页
- W2：备份/导出 + 审计页 + 权限打磨 + UAT

## 12) MVP验收标准
- 可按项目配置MySQL连接并测试成功
- 可发起生产查询工单并走审批后执行
- 可导出查询结果（脱敏+token下载）
- 可发起备份并下载备份包
- 全链路审计可追溯（申请-审批-执行-下载）

如果你确认这版方案，我下一步可以直接给你：
1) **SQL迁移脚本**（新增5张表 + 索引）
2) **后端接口骨架代码**（FastAPI路由 + service）
3) **前端页面骨架**（连接管理/SQL工单/备份导出）
