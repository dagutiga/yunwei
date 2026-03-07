# Jenkins CI/CD + Ansible 初始化 实施方案（可开工版）

## 1. 目标与原则

本方案用于将 PRD 落地为可直接排期开发的任务，覆盖 SQL、后端、前端、联调与验收。

实施原则：

1. 优先复用现有项目 RBAC 与审批能力（admin/owner/member）。
2. 所有高风险操作必须可审计（谁、何时、做了什么、结果如何）。
3. 初始化/发布任务采用异步执行，避免阻塞 API。
4. 日志“先落库后推送”，保证页面中断后可追溯。

---

## 2. SQL 变更清单

迁移脚本已提供：`backend/sql_migration_cicd_ansible.sql`。

### 2.1 新增与变更

1. 变更 `virtual_machines`：新增初始化状态字段（`init_status` 等）。
2. 新增 `jenkins_configs`：项目级 Jenkins 连接配置。
3. 新增 `jenkins_pipelines`：流水线缓存与参数模板。
4. 新增 `deploy_tasks`：部署审批与执行记录。
5. 新增 `vm_init_jobs`：初始化任务主表。
6. 新增 `vm_init_logs`：初始化日志明细（支持增量拉取和流式展示）。

### 2.2 执行建议

1. 先测试库执行并回归现有功能（登录、VM 查询、审批、导出）。
2. 生产库在业务低峰执行，执行前做全量备份。
3. 执行后检查表结构与索引，再灰度发布后端。

---

## 3. 后端实施方案（FastAPI）

## 3.1 模块拆分建议

建议在 `backend/core/` 下新增：

1. `jenkins_client.py`：Jenkins API 封装（配置校验、同步 Pipeline、触发构建、查状态）。
2. `task_runner.py`：异步任务执行器（可先线程池 + DB 轮询，后续可迁移 Celery）。
3. `ansible_runner.py`：调用 `ansible-playbook` 并解析 stdout/stderr 事件。

## 3.2 新增 API 清单

### Jenkins 与 Pipeline

1. `POST /api/cicd/jenkins/config`
   - 入参：`project_id, base_url, username, token, default_folder, is_enabled`
   - 鉴权：admin / owner
   - 输出：配置 ID

2. `POST /api/cicd/jenkins/test`
   - 入参：`project_id`
   - 行为：读取密文 token，解密后访问 Jenkins `whoAmI`/crumb 接口

3. `POST /api/cicd/pipelines/sync`
   - 入参：`project_id`
   - 行为：从 Jenkins 拉取 jobs，同步到 `jenkins_pipelines`

4. `GET /api/cicd/pipelines`
   - 入参：`project_id`
   - 输出：流水线列表 + 可用环境 + 参数模板

### 部署任务

5. `POST /api/cicd/deploy/trigger`
   - 入参：`project_id, pipeline_id, target_env, params, change_log`
   - 行为：
     - dev/staging：直接 `RUNNING`，异步触发 Jenkins
     - prod：创建审批态（member: owner->admin；owner: admin）

6. `GET /api/cicd/deploy/list`
   - 入参：`project_id, target_env, state, keyword, page, page_size`

7. `GET /api/cicd/deploy/{task_id}`
   - 输出：审批链、Jenkins build 信息、失败原因、耗时

8. `POST /api/cicd/tasks/{task_id}/approve`
   - 入参：`action, comment`
   - 行为：复用既有审批风格，审批通过后触发执行

### VM 初始化

9. `POST /api/vm/init/start`
   - 入参：`vm_id`
   - 行为：
     - 校验项目权限 + SSH 凭据可用
     - 若已有 RUNNING 任务则返回冲突
     - 创建 `vm_init_jobs`，将 VM 状态置为 `INIT_RUNNING`
     - 异步调用 Ansible

10. `GET /api/vm/init/{job_id}`
   - 输出：任务状态、开始结束时间、错误摘要

11. `GET /api/vm/init/{job_id}/logs`
   - 入参：`cursor_seq, limit`
   - 输出：增量日志（用于断线重连）

12. `GET /api/vm/init/stream/{job_id}`（SSE）
   - 输出：实时日志事件流（`event: log/status/end`）

## 3.3 状态机定义

### deploy_tasks.state

1. `PENDING_OWNER_APPROVAL`
2. `PENDING_ADMIN_APPROVAL`
3. `RUNNING`
4. `SUCCESS`
5. `FAILED`
6. `REJECTED`
7. `CANCELED`
8. `TRIGGER_FAILED`

### vm_init_jobs.state

1. `INIT_RUNNING`
2. `INIT_DONE`
3. `INIT_FAILED`
4. `CANCELED`

### virtual_machines.init_status

1. `INIT_PENDING`
2. `INIT_RUNNING`
3. `INIT_DONE`
4. `INIT_FAILED`

## 3.4 Ansible 执行规范

### Playbook 步骤（固定顺序）

1. `JDK_INSTALL`：统一 JDK 版本（建议参数化 `target_jdk_version`）。
2. `APPUSER_CREATE`：创建 `appuser` 并授予 sudo 组策略。
3. `JENKINS_SSH_TRUST`：下发 Jenkins 公钥到 `authorized_keys`。
4. `COMMON_TOOLS_INSTALL`：安装基础工具包。
5. `VERIFY`：执行 `java -version`、`id appuser`、工具命令检查。

### 执行要求

1. 仅允许使用平台内配置的 Jenkins 公钥（禁用用户输入公钥）。
2. 每个步骤都要写入 `vm_init_logs`（成功/失败都写）。
3. 失败即终止，记录失败步骤与 stderr 摘要。

## 3.5 配置项（.env）建议新增

1. `JENKINS_TIMEOUT=15`
2. `JENKINS_VERIFY_SSL=true`
3. `JENKINS_PUBKEY_PATH=/app/yunwei/backend/keys/jenkins_id_rsa.pub`
4. `ANSIBLE_PLAYBOOK_PATH=/app/yunwei/backend/ansible/init_vm.yml`
5. `ANSIBLE_INVENTORY_MODE=dynamic`
6. `TASK_POLL_INTERVAL_SEC=5`

---

## 4. 前端实施方案（Vue3 + Element Plus）

## 4.1 页面改造点

1. `frontend/src/views/MainView.vue`
   - 顶部新增“CI/CD中心”按钮。
   - VM 操作列新增“初始化”按钮（按 `init_status` 控制可用性）。
   - 新增初始化状态列（INIT_PENDING/RUNNING/DONE/FAILED）。

2. 新增 `frontend/src/views/CicdView.vue`
   - Pipeline 列表
   - 触发表单（环境、参数、变更说明）
   - 部署记录表（状态、审批、日志跳转）

3. 新增 `frontend/src/components/InitLogDrawer.vue`
   - 展示实时日志流
   - 断线自动重连 + 游标补拉

## 4.2 API 封装新增

在 `frontend/src/api/` 新增 `cicd.js`，并补充 `vm.js`：

1. Jenkins 配置与测试接口
2. Pipeline 同步与查询接口
3. 部署触发/查询/审批接口
4. 初始化任务启动/状态/日志接口

## 4.3 关键交互

1. 点击“初始化”后弹确认框，确认后启动任务并自动打开日志抽屉。
2. 日志抽屉默认先调 `/logs` 拉历史，再连接 `/stream` 收实时。
3. 状态变化时更新 VM 列表行状态和按钮可用性。
4. prod 触发按钮文案为“提交审批”，非 prod 为“立即触发”。

---

## 5. 开发任务拆解（建议 Jira 颗粒度）

## 5.1 后端任务

1. 数据库迁移脚本评审与执行。
2. Jenkins 客户端封装与异常码规范。
3. Pipeline 同步接口开发。
4. 部署触发/审批/状态轮询链路开发。
5. 初始化任务执行器与日志落库。
6. SSE 日志流接口开发。
7. 权限与审计日志补齐。

## 5.2 前端任务

1. 路由新增 `CicdView`。
2. CI/CD 页面开发（列表、筛选、触发表单、记录）。
3. VM 列表增加初始化按钮与状态展示。
4. 初始化日志抽屉组件开发（含断线重连）。
5. 审批中心兼容 DEPLOY 类型展示。

## 5.3 测试任务

1. API 冒烟（权限、参数校验、状态流转）。
2. Jenkins 不可用/鉴权失败/任务不存在异常用例。
3. 初始化成功/失败/中断恢复用例。
4. 兼容回归：VM 管理、下线检查、审批、导出。

---

## 6. 联调与验收计划

## 6.1 里程碑（2 周冲刺版）

1. D1-D3：后端数据模型 + Jenkins 基础接口 + 初始化任务主流程。
2. D4-D6：前端 CI/CD 页面 + 初始化日志抽屉。
3. D7-D8：联调与异常修复。
4. D9-D10：灰度验证 + UAT。

## 6.2 发布前检查清单

1. SQL 已在测试/预发通过。
2. Jenkins 测试环境 token 与公钥已配置。
3. Ansible Playbook 在 2 种 Linux 发行版验证通过。
4. prod 审批链路验证通过（member->owner->admin）。
5. 初始化日志断线重连验证通过。

---

## 7. 关键风险与兜底

1. Jenkins 接口差异：以最小 API 集合接入，失败时给出明确错误码。
2. Ansible 运行环境不一致：固定执行用户、Python 解释器、Playbook 版本。
3. 日志流丢失：采用“DB 游标补偿 + SSE 实时推送”双通道。
4. 并发冲突：部署与初始化均加“同目标单任务运行”约束。
