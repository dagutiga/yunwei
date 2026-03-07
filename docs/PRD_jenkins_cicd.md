# PRD：Jenkins CI/CD 能力接入（yunwei）

## 1. 文档信息

- 产品名称：虚拟机自助管理系统（yunwei）
- 需求名称：Jenkins CI/CD 能力接入
- 版本：V1.0（MVP）
- 目标上线：T+4 周
- 文档状态：评审稿

---

## 2. 背景与问题定义

当前系统已具备「项目管理、VM 资产管理、下线检查、审批流程、SSH 运维」能力，但缺少与研发交付链路（构建/部署）的打通能力，导致：

1. 发布流程分散在 Jenkins 与运维平台之外，状态不可见。
2. 缺少统一审批闸口，发布行为与资产变更无法形成闭环记录。
3. 故障回溯效率低，难以快速定位“谁在何时向哪台机器部署了哪个版本”。

**本需求目标**：在现有项目维度和权限体系下，接入 Jenkins Pipeline，实现“可触发、可审批、可审计、可回滚”的 CI/CD 最小闭环。

---

## 3. 产品目标与成功指标

## 3.1 业务目标

- 提升发布效率：减少跨系统切换与人工传话。
- 降低发布风险：将生产发布纳入审批与可追踪流程。
- 提升可审计性：形成完整发布日志与责任链路。

## 3.2 核心指标（上线后 30 天）

- 发布任务在线发起率 >= 70%（线上发布中通过本系统发起比例）。
- 生产发布审批覆盖率 = 100%。
- 发布失败平均定位时长（MTTR-Trace）下降 >= 30%。
- 成功发布率 >= 95%（非代码问题导致失败不计入）。

---

## 4. 适用范围（MVP）

## 4.1 In Scope

1. Jenkins 连接配置（按项目绑定）。
2. Pipeline 清单管理（拉取/选择/启停）。
3. 构建触发（手动触发，支持参数）。
4. 发布审批（复用现有审批中心，新增“部署任务”类型）。
5. 构建状态追踪（队列中/执行中/成功/失败/取消）。
6. 构建日志查看（概要日志 + Jenkins 原始日志跳转）。
7. 发布记录审计（发起人、审批人、目标项目/环境、构建号、结果）。
8. 服务器录入后的 Ansible 初始化（含过程实时展示与初始化标准化）。

## 4.2 Out of Scope（后续版本）

- 多 CI 平台适配（GitLab CI、GitHub Actions）。
- 自动化回滚编排（MVP 仅支持“触发回滚 Pipeline”）。
- 蓝绿/金丝雀发布策略编排。
- Webhook 自动触发（MVP 先手动触发，V1.1 支持代码事件触发）。
- 自动化配置漂移修复（MVP 先做首次初始化，不做持续对账修复）。

---

## 5. 目标用户与角色权限

## 5.1 角色

- 管理员（admin）：全局配置、审批、审计查看。
- 项目负责人（owner）：项目内配置 Jenkins、审批成员发起的发布。
- 项目成员（member）：发起构建/部署申请，查看本项目记录。

## 5.2 权限规则（MVP）

1. Jenkins 连接配置：admin + 项目 owner。
2. 触发 dev/staging：owner/member 可直接触发。
3. 触发 prod：
   - member 发起 -> owner 审批 -> admin 审批 -> 执行；
   - owner 发起 -> admin 审批 -> 执行。
4. 发布记录导出：admin + 项目 owner。

---

## 6. 典型用户故事（User Stories）

1. 作为项目 owner，我希望为项目绑定 Jenkins 地址和 Token，以便成员在平台内统一触发发布。
2. 作为项目 member，我希望选择 Pipeline 与参数后提交部署申请，以便无需登录 Jenkins 也能发版。
3. 作为审批人（owner/admin），我希望看到发布目标环境、构建参数与变更说明，以便做风险判断。
4. 作为运维/管理者，我希望查看每次发布的执行轨迹与日志链接，以便出现问题时快速追溯。
5. 作为管理员，我希望限制高风险操作（prod 发布必须审批），以确保合规。
6. 作为运维人员，我希望服务器录入后可一键执行 Ansible 初始化，并在页面实时看到执行过程，以便确认机器达到可用基线。

---

## 7. 业务流程

## 7.1 主流程：生产部署（member 发起）

1. member 进入“CI/CD”页，选择项目、Pipeline、环境=prod，填写参数（版本号、变更说明等）。
2. 系统校验权限与必填参数，通过后创建 `DEPLOY` 类型任务，状态=`PENDING_OWNER_APPROVAL`。
3. owner 在审批中心通过后，状态流转到 `PENDING_APPROVAL`（管理员审批）。
4. admin 审批通过后，系统调用 Jenkins Build API 触发构建，任务状态=`RUNNING`。
5. 系统轮询 Jenkins 构建结果：
   - 成功 -> `SUCCESS`；
   - 失败 -> `FAILED`；
   - 取消 -> `CANCELED`。
6. 结果同步到“发布记录”，展示构建号、执行时长、日志链接。

## 7.2 分支流程

- **驳回**：任一审批节点驳回，状态=`REJECTED`，记录驳回原因。
- **非生产环境**：dev/staging 可直接触发，跳过审批（可配置开关，默认开启直发）。
- **Jenkins 不可用**：任务进入 `TRIGGER_FAILED`，提示“连接失败/鉴权失败/任务不存在”。

## 7.3 服务器初始化流程（录入后）

1. 用户在“录入虚拟机”成功后，系统将该 VM 标记为 `INIT_PENDING`。
2. 用户点击“Ansible 初始化”，系统创建初始化任务并分配 `job_id`。
3. 后端调用 Ansible Playbook，按步骤执行：
   - 统一 JDK 版本；
   - 创建 `appuser`（具备 sudo 权限组）；
   - 配置 Jenkins 服务器免密登录；
   - 安装常用命令工具。
4. 前端在当前页面实时展示执行日志（WebSocket/SSE 方式），显示当前步骤、成功/失败状态。
5. 初始化成功后 VM 状态更新为 `INIT_DONE`，失败则为 `INIT_FAILED` 并展示失败步骤。

---

## 8. 功能需求明细

## 8.1 Jenkins 连接管理（项目维度）

### 功能点

- 新增 Jenkins 连接配置：
  - Jenkins URL
  - 用户名/API Token（加密存储）
  - 默认 Folder（可选）
  - 连通性测试按钮
- 支持启用/停用连接。

### 规则

- 一个项目可配置 1 个默认 Jenkins 连接（MVP）。
- Token 仅保存密文，页面仅展示脱敏值。

## 8.2 Pipeline 管理

### 功能点

- 从 Jenkins 拉取 Job/Pipeline 列表。
- 标记可用环境（dev/staging/prod）。
- 配置参数模板（如 `branch`, `image_tag`, `deploy_env`）。

### 规则

- 仅可选择“已启用”的 Pipeline 进行触发。
- prod 环境必须绑定审批策略。

## 8.3 发布触发

### 功能点

- 选择 Pipeline + 环境 + 参数 -> 发起部署。
- 非 prod 直接触发；prod 走审批。
- 展示触发结果与 Jenkins queue/build 编号。

### 规则

- 必填参数不完整时不可提交。
- 同一项目同一环境同一 Pipeline 同时仅允许 1 个 RUNNING 任务（防并发踩踏）。

## 8.4 审批与执行

### 功能点

- 审批中心新增任务类型：`DEPLOY`。
- 审批卡片展示：目标环境、Pipeline、参数摘要、变更说明、发起人。
- 审批动作：通过/驳回。

### 规则

- 审批链与现有 OFFLINE/DELETE 保持一致风格。
- 审批通过后由后端异步触发 Jenkins，避免接口超时。

## 8.5 发布记录与审计

### 功能点

- 发布记录列表：按项目/环境/状态/时间筛选。
- 详情查看：审批链路、Jenkins Build URL、日志摘要。
- 导出 Excel（与现有导出能力一致）。

### 规则

- 数据至少保留 180 天。
- 关键字段不可篡改（仅补充系统备注）。

## 8.6 服务器初始化（Ansible）

### 功能点

- VM 列表新增“初始化”按钮（仅 `INIT_PENDING/INIT_FAILED` 可点击）。
- 初始化任务执行时，页面实时输出 Ansible 过程日志。
- 支持查看最近一次初始化结果与执行明细。

### 初始化标准（MVP）

1. **统一 JDK 版本**：按平台配置安装指定版本（如 JDK 17），并校验 `java -version`。
2. **创建 appuser**：创建 `appuser`，加入 sudo 权限组（最小权限建议配置命令白名单）。
3. **Jenkins 免密登录**：将 Jenkins 公钥写入目标机 `authorized_keys`，验证可免密 SSH。
4. **常用命令安装**：安装基础工具（如 `curl`, `wget`, `git`, `unzip`, `vim`, `net-tools`）。

### 规则

- 初始化前需校验 VM SSH 凭据可用。
- 同一 VM 同时仅允许 1 个初始化任务运行。
- 初始化日志需完整落库，便于审计和故障定位。

---

## 9. 原型说明（文字版）

## 9.1 主界面新增入口

- 位置：主页面顶部操作区新增按钮“CI/CD中心”。
- 点击后进入二级页（或右侧抽屉，优先推荐二级页）。

## 9.2 CI/CD 中心页面结构

1. 顶部筛选区：项目、环境、状态、关键字。
2. 左侧（或上半区）：Pipeline 列表（名称、可用环境、最后构建状态）。
3. 右侧（或下半区）：触发面板（参数输入、变更说明、触发按钮）。
4. 下方：构建记录表（任务ID、Pipeline、环境、状态、发起人、审批人、时间、日志）。

## 9.3 交互细节

- 触发 prod 时，按钮文案为“提交审批”；非 prod 为“立即触发”。
- 状态标签颜色：
  - RUNNING 蓝色
  - SUCCESS 绿色
  - FAILED 红色
  - PENDING_* 橙色
- 日志支持“查看摘要”和“打开 Jenkins 原始日志”两种模式。

---

## 10. 数据模型（建议新增）

1. `jenkins_configs`
   - id, project_id, base_url, username, token_cipher, default_folder, is_enabled, create_user_id, create_time
2. `jenkins_pipelines`
   - id, project_id, config_id, pipeline_name, display_name, env_scope, param_schema_json, is_enabled, update_time
3. `deploy_tasks`
   - id, project_id, pipeline_id, env, params_json, change_log, state, request_user_id,
     owner_approval_user_id, admin_approval_user_id, jenkins_queue_id, jenkins_build_number,
     jenkins_build_url, result, duration_sec, create_time, update_time

> 说明：也可复用现有 `workflow_tasks` 扩展 task_type=`DEPLOY`，但建议将“审批流任务”与“CI 执行记录”拆表，便于后续扩展多平台和重试机制。

---

## 11. 接口设计（MVP）

1. `POST /api/cicd/jenkins/config`：创建/更新 Jenkins 配置。
2. `POST /api/cicd/jenkins/test`：测试连通性。
3. `GET /api/cicd/pipelines`：查询 Pipeline 列表。
4. `POST /api/cicd/pipelines/sync`：同步 Jenkins Pipeline。
5. `POST /api/cicd/deploy/trigger`：触发或提交审批。
6. `GET /api/cicd/deploy/list`：查询发布记录。
7. `GET /api/cicd/deploy/{id}`：查询发布详情。
8. `POST /api/cicd/tasks/{task_id}/approve`：审批 DEPLOY 任务。
9. `POST /api/vm/init/start`：启动 Ansible 初始化任务。
10. `GET /api/vm/init/{job_id}`：查询初始化任务状态。
11. `GET /api/vm/init/{job_id}/logs`：获取初始化日志（支持分页/增量游标）。
12. `GET /api/vm/init/stream/{job_id}`：实时日志流（SSE/WebSocket）。

---

## 12. 异常与风控

1. Jenkins 凭证错误：提示“鉴权失败”，禁止触发。
2. Pipeline 不存在：提示“配置失效，请同步 Pipeline”。
3. 并发冲突：同环境同 Pipeline 有运行中任务时阻止再次触发。
4. 审批超时：超过 24h 自动取消（可配置）。
5. 高风险环境保护：prod 必须审批，且需填写变更说明。
6. 初始化阶段连接中断：任务标记 `INIT_FAILED`，保留最后成功步骤与错误信息。
7. 免密配置风险：仅允许写入平台配置的 Jenkins 公钥，禁止页面自由输入公钥。

---

## 13. 验收标准（UAT）

## 13.1 功能验收

- [ ] owner 可完成 Jenkins 配置并测试连通成功。
- [ ] 成员可在 dev/staging 直接触发 Pipeline 并看到结果。
- [ ] 成员触发 prod 时会进入审批流程，未审批不执行。
- [ ] owner 与 admin 按顺序审批后，任务可自动调用 Jenkins 执行。
- [ ] 发布记录可查询到“发起-审批-执行-结果”全链路。
- [ ] VM 录入后可执行 Ansible 初始化，且页面实时可见执行过程。
- [ ] 初始化成功后可校验 JDK 版本、appuser、免密登录、常用命令安装结果。

## 13.2 安全与权限验收

- [ ] 非项目成员无法查看/触发项目 Pipeline。
- [ ] 非 owner/admin 无法修改 Jenkins 配置。
- [ ] 凭证字段以密文存储、页面脱敏显示。

## 13.3 稳定性验收

- [ ] Jenkins 短暂不可用时，系统返回明确错误并记录失败原因。
- [ ] 发布状态轮询准确率 >= 99%。
- [ ] 100 并发查询下，发布列表接口 P95 < 500ms。
- [ ] 初始化日志流中断可恢复，且不会丢失已落库日志。

---

## 14. 埋点与数据看板

1. 触发事件：`deploy_trigger_clicked`（项目、环境、Pipeline、角色）。
2. 审批事件：`deploy_approved` / `deploy_rejected`。
3. 执行事件：`deploy_started` / `deploy_finished`（result, duration）。
4. 初始化事件：`vm_init_started` / `vm_init_step_finished` / `vm_init_finished`。
5. 看板指标：
   - 发布次数（日/周）
   - 成功率
   - 审批耗时
   - 失败 Top 原因
   - 初始化成功率
   - 初始化平均耗时

---

## 15. 上线计划与里程碑

## 第 1 周：方案与设计

- 完成 PRD 评审、接口评审、数据库评审。
- 完成高保真原型与字段字典。

## 第 2-3 周：开发联调

- 后端：配置管理、触发、轮询、审批流接入。
- 前端：CI/CD 页面、触发表单、记录页、审批展示。
- 联调 Jenkins 测试环境。

## 第 4 周：测试与灰度

- 完成功能/权限/异常测试。
- 先灰度 1-2 个项目，观察一周后全量。

---

## 16. 风险与应对

1. Jenkins 接口差异（插件版本差异）
   - 应对：封装 Jenkins 适配层，先支持标准 Pipeline API。
2. Token 管理风险
   - 应对：统一密钥加密存储 + 最小权限 Token。
3. 审批链过长影响效率
   - 应对：仅 prod 强制双审批，非 prod 直发。
4. 发布失败定位复杂
   - 应对：任务详情内保留参数快照与 Jenkins 链接。
5. Ansible 剧本执行不一致（OS 差异）
   - 应对：按系统发行版维护 Playbook 变量，先支持主流 Linux。

---

## 17. 后续迭代（V1.1+）

1. Git Webhook 自动触发（commit/tag 触发）。
2. 回滚向导（一键回滚到上一个稳定版本）。
3. 多 CI 平台接入。
4. 发布策略模板（滚动、蓝绿、金丝雀）。
