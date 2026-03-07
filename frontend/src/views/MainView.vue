<template>
  <div class="main-container">
    <!-- 顶部导航 -->
    <header class="header-wrap">
      <div class="header-left">
        <div class="logo">
          <el-icon :size="28"><Monitor /></el-icon>
          <span class="logo-text">云威<span class="highlight">VM</span>管理</span>
        </div>
        <div class="header-line"></div>
        <el-text size="large" tag="b" class="version-text">v1.1</el-text>
      </div>

      <div class="header-center">
        <div class="user-info">
          <div class="user-avatar">
            <el-icon :size="18"><User /></el-icon>
          </div>
          <span class="user-name">{{ userStore.username || '-' }}</span>
          <el-tag :type="userStore.role === 'admin' ? 'danger' : 'success'" effect="dark" size="small" class="role-tag">
            {{ userStore.role === 'admin' ? '管理员' : '用户' }}
          </el-tag>
        </div>
      </div>

      <div class="header-right">
        <el-button class="tech-btn" @click="loadAll">
          <el-icon><Refresh /></el-icon>
          <span>刷新</span>
        </el-button>
        <el-button v-if="userStore.role === 'admin'" class="tech-btn" @click="openUserDialog">
          <el-icon><Setting /></el-icon>
          <span>用户管理</span>
        </el-button>
        <el-button class="tech-btn danger" @click="handleLogout">
          <el-icon><SwitchButton /></el-icon>
          <span>退出</span>
        </el-button>
      </div>
    </header>

    <!-- 主内容区 -->
    <main class="main-wrap">
      <!-- 筛选栏 -->
      <div class="filter-bar">
        <div class="filter-left">
          <el-select v-model="filters.project_id" placeholder="选择项目" clearable class="tech-select" @change="loadVMList">
            <el-option v-for="item in projects" :key="item.id" :label="item.project_name" :value="item.id" />
          </el-select>
          <el-input v-model="filters.keyword" placeholder="搜索 VM/IP/项目" clearable class="tech-input" @keyup.enter="loadVMList">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <el-button type="primary" class="tech-btn-primary" @click="loadVMList">
            <el-icon><Search /></el-icon>
            查询
          </el-button>
        </div>
        <div class="filter-right">
          <el-button class="tech-btn-success" @click="showAddVM = true">
            <el-icon><Plus /></el-icon>
            录入虚拟机
          </el-button>
          <el-button v-if="canManageProject" class="tech-btn" @click="openMemberDialog">
            <el-icon><UserFilled /></el-icon>
            项目成员
          </el-button>
          <el-button v-if="userStore.role === 'admin'" class="tech-btn" @click="showProjectDialog = true">
            <el-icon><FolderAdd /></el-icon>
            创建项目
          </el-button>
          <el-button v-if="canExport" class="tech-btn-export" @click="handleExport">
            <el-icon><Download /></el-icon>
            导出
          </el-button>
        </div>
      </div>

      <!-- VM列表 -->
      <div class="content-card">
        <div class="card-header">
          <div class="card-title">
            <el-icon><Grid /></el-icon>
            <span>虚拟机列表</span>
          </div>
          <div class="card-stats">
            <span class="stat-item">
              <span class="stat-dot running"></span>
              运行中
            </span>
            <span class="stat-item">
              <span class="stat-dot stopped"></span>
              已停止
            </span>
            <span class="stat-total">共 {{ vmList.length }} 台</span>
          </div>
        </div>
        <el-table :data="vmList" border style="width: 100%;" height="320" class="tech-table">
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="project_name" label="项目" width="120" />
          <el-table-column prop="vm_name" label="VM名称" min-width="130" />
          <el-table-column prop="ip_address" label="IP" width="130">
            <template #default="scope">
              <span class="ip-text">{{ scope.row.ip_address }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="environment" label="环境" width="80">
            <template #default="scope">
              <el-tag :type="getEnvType(scope.row.environment)" size="small" effect="dark">{{ scope.row.environment }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="power_state" label="运行状态" width="90">
            <template #default="scope">
              <span :class="['status-badge', scope.row.power_state === 'running' ? 'running' : 'stopped']">
                {{ scope.row.power_state }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="offline_status" label="下线状态" width="110" />
          <el-table-column prop="offline_check_result" label="检查结果" width="90" />
          <el-table-column label="操作" fixed="right" width="320">
            <template #default="scope">
              <div class="action-buttons">
                <el-button size="small" class="action-btn ssh" @click="selectVM(scope.row)">
                  <el-icon><Monitor /></el-icon>SSH
                </el-button>
                <el-button size="small" class="action-btn check" @click="handleCheck(scope.row)">
                  <el-icon><Check /></el-icon>检查
                </el-button>
                <el-button size="small" class="action-btn offline" @click="openOfflineDialog(scope.row)">
                  <el-icon><SwitchButton /></el-icon>下线
                </el-button>
                <el-button size="small" class="action-btn delete" @click="openDeleteDialog(scope.row)">
                  <el-icon><Delete /></el-icon>删除
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 底部面板 -->
      <div class="bottom-panels">
        <div class="content-card half">
          <div class="card-header">
            <div class="card-title">
              <el-icon><Document /></el-icon>
              <span>下线检查详情</span>
            </div>
            <el-tag v-if="offlineResult" :type="offlineResult?.result === 'pass' ? 'success' : 'warning'" effect="dark">
              {{ offlineResult?.result || '-' }}
            </el-tag>
          </div>
          <div class="panel-content">
            <el-descriptions v-if="currentCheckVM" :column="1" border size="small" class="tech-desc">
              <el-descriptions-item label="VM">{{ currentCheckVM.vm_name }}</el-descriptions-item>
              <el-descriptions-item label="L1阻断">
                <span v-if="!offlineResult?.l1?.length" class="text-success">无</span>
                <span v-else class="text-danger">{{ offlineResult.l1.map(i => i.title).join('；') }}</span>
              </el-descriptions-item>
              <el-descriptions-item label="L2风险">
                <span v-if="!offlineResult?.l2?.length" class="text-success">无</span>
                <span v-else class="text-warning">{{ offlineResult.l2.map(i => i.title).join('；') }}</span>
              </el-descriptions-item>
              <el-descriptions-item label="L3人工确认">
                {{ offlineResult?.l3?.map(i => i.title).join('；') || '-' }}
              </el-descriptions-item>
            </el-descriptions>
            <el-empty v-else description="请先执行下线检查" />
          </div>
        </div>

        <div class="content-card half">
          <div class="card-header">
            <div class="card-title">
              <el-icon><List /></el-icon>
              <span>审批中心</span>
            </div>
            <el-button size="small" class="tech-btn-mini" @click="loadTasks">
              <el-icon><Refresh /></el-icon>刷新
            </el-button>
          </div>
          <el-tabs class="tech-tabs">
            <el-tab-pane label="我的申请">
              <el-table :data="myTasks" border size="small" height="180" class="tech-table-mini">
                <el-table-column prop="id" label="ID" width="50" />
                <el-table-column prop="task_type" label="类型" width="80" />
                <el-table-column prop="vm_name" label="VM" min-width="100" />
                <el-table-column prop="state" label="状态" min-width="100">
                  <template #default="scope">
                    <span :class="['state-badge', scope.row.state]">{{ scope.row.state }}</span>
                  </template>
                </el-table-column>
              </el-table>
            </el-tab-pane>
            <el-tab-pane label="待审批">
              <el-table :data="pendingTasks" border size="small" height="180" class="tech-table-mini">
                <el-table-column prop="id" label="ID" width="50" />
                <el-table-column prop="task_type" label="类型" width="70" />
                <el-table-column prop="vm_name" label="VM" min-width="90" />
                <el-table-column prop="requester" label="发起人" width="70" />
                <el-table-column label="操作" width="120">
                  <template #default="scope">
                    <el-button size="small" type="success" class="mini-btn pass" @click="approve(scope.row.id, 'approve')">通过</el-button>
                    <el-button size="small" type="danger" class="mini-btn reject" @click="approve(scope.row.id, 'reject')">驳回</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </el-tab-pane>
          </el-tabs>
        </div>
      </div>

      <!-- SSH终端 -->
      <div v-if="selectedVM" class="content-card terminal-card">
        <div class="card-header">
          <div class="card-title">
            <el-icon><Monitor /></el-icon>
            <span>{{ selectedVM.vm_name }} - SSH终端</span>
          </div>
          <el-button size="small" class="tech-btn-mini" @click="selectedVM = null">
            <el-icon><Close /></el-icon>关闭
          </el-button>
        </div>
        <SSHTerminal :vm-id="selectedVM.id" />
      </div>
    </main>

    <!-- 弹窗们 -->
    <el-dialog v-model="showAddVM" title="录入虚拟机" width="580px" class="tech-dialog">
      <el-form :model="vmForm" label-width="100px" class="tech-form">
        <el-form-item label="所属项目" required>
          <el-select v-model="vmForm.project_id" style="width: 100%;">
            <el-option v-for="item in projects" :key="item.id" :label="item.project_name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="VM名称" required><el-input v-model="vmForm.vm_name" /></el-form-item>
        <el-form-item label="IP" required><el-input v-model="vmForm.ip_address" /></el-form-item>
        <el-form-item label="环境">
          <el-select v-model="vmForm.environment" style="width: 100%;">
            <el-option label="prod" value="prod" />
            <el-option label="staging" value="staging" />
            <el-option label="dev" value="dev" />
          </el-select>
        </el-form-item>
        <el-form-item label="负责人"><el-input v-model="vmForm.owner_name" /></el-form-item>
        <el-form-item label="SSH用户" required><el-input v-model="vmForm.ssh_user" /></el-form-item>
        <el-form-item label="SSH密码" required><el-input v-model="vmForm.ssh_password" type="password" /></el-form-item>
        <el-form-item label="OS"><el-input v-model="vmForm.os_type" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="vmForm.remark" type="textarea" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddVM = false">取消</el-button>
        <el-button type="primary" @click="handleAddVM">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showOfflineDialog" title="申请下线" width="640px" class="tech-dialog">
      <el-form :model="offlineForm" label-width="120px" class="tech-form">
        <el-form-item label="L3-数据迁移"><el-switch v-model="offlineForm.data_migrated" /></el-form-item>
        <el-form-item label="L3-依赖解除"><el-switch v-model="offlineForm.dependency_cleared" /></el-form-item>
        <el-form-item label="L3-干系人通知"><el-switch v-model="offlineForm.stakeholders_notified" /></el-form-item>
        <el-divider>强制下线（仅负责人/管理员）</el-divider>
        <el-form-item label="强制下线"><el-switch v-model="offlineForm.force_offline" /></el-form-item>
        <el-form-item label="强制原因"><el-input v-model="offlineForm.force_reason" type="textarea" /></el-form-item>
        <el-form-item label="风险确认"><el-input v-model="offlineForm.risk_ack" type="textarea" /></el-form-item>
        <el-form-item label="回滚预案"><el-input v-model="offlineForm.rollback_plan" type="textarea" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showOfflineDialog = false">取消</el-button>
        <el-button type="warning" @click="handleApplyOffline">提交申请</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showDeleteDialog" title="申请删除（不可逆）" width="520px" class="tech-dialog">
      <el-alert title="请确认删除前已经通过下线检查。" type="warning" show-icon :closable="false" />
      <el-form :model="deleteForm" label-width="100px" style="margin-top: 10px;">
        <el-form-item label="二次确认" required>
          <el-input v-model="deleteForm.confirm_text" placeholder="请输入 DELETE" />
        </el-form-item>
        <el-form-item label="删除原因">
          <el-input v-model="deleteForm.reason" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDeleteDialog = false">取消</el-button>
        <el-button type="danger" @click="handleApplyDelete">提交删除申请</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showProjectDialog" title="创建项目" width="480px" class="tech-dialog">
      <el-form :model="projectForm" label-width="80px" class="tech-form">
        <el-form-item label="项目名" required><el-input v-model="projectForm.project_name" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="projectForm.description" type="textarea" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showProjectDialog = false">取消</el-button>
        <el-button type="primary" @click="handleCreateProject">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showMemberDialog" title="项目成员配置" width="540px" class="tech-dialog">
      <el-form :model="memberForm" label-width="80px" class="tech-form">
        <el-form-item label="项目" required>
          <el-select v-model="memberForm.project_id" style="width: 100%;">
            <el-option v-for="item in projects" :key="item.id" :label="item.project_name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="用户名" required>
          <el-select
            v-model="memberForm.username"
            filterable
            allow-create
            default-first-option
            clearable
            placeholder="请选择或输入用户名"
            style="width: 100%;"
          >
            <el-option v-for="item in users" :key="item.id" :label="item.username" :value="item.username" />
          </el-select>
        </el-form-item>
        <el-form-item label="角色" required>
          <el-select v-model="memberForm.role" style="width: 100%;">
            <el-option label="owner" value="owner" />
            <el-option label="member" value="member" />
          </el-select>
        </el-form-item>
        <el-form-item label="有效期">
          <el-date-picker v-model="memberForm.valid_until" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" style="width: 100%;" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showMemberDialog = false">取消</el-button>
        <el-button type="primary" @click="handleUpsertMember">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showUserDialog" title="用户管理（管理员）" width="720px" class="tech-dialog">
      <el-row :gutter="16">
        <el-col :span="12">
          <div class="dialog-card">
            <div class="dialog-card-header">
              <el-icon><UserFilled /></el-icon>
              <span>创建普通用户</span>
            </div>
            <el-form :model="createUserForm" label-width="80px">
              <el-form-item label="用户名" required><el-input v-model="createUserForm.username" /></el-form-item>
              <el-form-item label="密码" required><el-input v-model="createUserForm.password" type="password" show-password /></el-form-item>
            </el-form>
            <el-button type="primary" @click="handleCreateUser" class="full-width">创建用户</el-button>
          </div>
        </el-col>
        <el-col :span="12">
          <div class="dialog-card">
            <div class="dialog-card-header">
              <el-icon><Lock /></el-icon>
              <span>重置用户密码</span>
            </div>
            <el-form :model="resetPwdForm" label-width="80px">
              <el-form-item label="用户名" required><el-input v-model="resetPwdForm.username" /></el-form-item>
              <el-form-item label="新密码" required><el-input v-model="resetPwdForm.new_password" type="password" show-password /></el-form-item>
            </el-form>
            <el-button type="warning" @click="handleResetPassword" class="full-width">重置密码</el-button>
          </div>
        </el-col>
      </el-row>

      <el-divider />
      <div class="card-header">
        <div class="card-title">
          <el-icon><User /></el-icon>
          <span>用户列表</span>
        </div>
      </div>
      <el-table :data="users" border size="small" height="200" class="tech-table-mini">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="username" label="用户名" min-width="140" />
        <el-table-column prop="create_time" label="创建时间" min-width="160" />
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Monitor, User, Refresh, Setting, SwitchButton, Search, Plus, UserFilled,
  FolderAdd, Download, Grid, Check, Delete, Document, List, Close, Lock
} from '@element-plus/icons-vue'
import { useUserStore } from '@/store/user'
import { createUser, getUsers, resetUserPassword } from '@/api/user'
import {
  addVM, applyDelete, applyOffline, approveTask, createProject, exportVMs,
  getMyTasks, getPendingTasks, getProjects, getVMList, offlineCheck, upsertProjectMember
} from '@/api/vm'
import SSHTerminal from '@/components/SSHTerminal.vue'

const router = useRouter()
const userStore = useUserStore()

const projects = ref([])
const vmList = ref([])
const selectedVM = ref(null)
const currentCheckVM = ref(null)
const offlineResult = ref(null)
const myTasks = ref([])
const pendingTasks = ref([])

const showAddVM = ref(false)
const showOfflineDialog = ref(false)
const showDeleteDialog = ref(false)
const showProjectDialog = ref(false)
const showMemberDialog = ref(false)
const showUserDialog = ref(false)

const users = ref([])
const createUserForm = ref({ username: '', password: '' })
const resetPwdForm = ref({ username: '', new_password: '' })

const filters = ref({ project_id: null, keyword: '' })

const vmForm = ref({
  project_id: null, vm_name: '', ip_address: '', ssh_port: 22,
  ssh_user: '', ssh_password: '', os_type: 'Linux', environment: 'prod',
  owner_name: '', cpu_cores: 2, memory_gb: 4, disk_gb: 50, remark: ''
})

const offlineForm = ref({
  vm_id: null, force_offline: false, force_reason: '', risk_ack: '',
  rollback_plan: '', data_migrated: false, dependency_cleared: false, stakeholders_notified: false
})

const deleteForm = ref({ vm_id: null, confirm_text: '', reason: '' })
const projectForm = ref({ project_name: '', description: '' })
const memberForm = ref({ project_id: null, username: '', role: 'member', valid_until: '' })

const currentProjectRole = computed(() => {
  const target = projects.value.find(item => item.id === filters.value.project_id)
  return target?.role || ''
})
const canManageProject = computed(() => userStore.role === 'admin' || currentProjectRole.value === 'owner')
const canExport = computed(() => userStore.role === 'admin' || currentProjectRole.value === 'owner')

const getEnvType = (env) => {
  const map = { prod: 'danger', staging: 'warning', dev: 'success' }
  return map[env] || ''
}

const loadProjects = async () => {
  const res = await getProjects()
  projects.value = res.data || []
  if (!filters.value.project_id && projects.value.length) {
    filters.value.project_id = projects.value[0].id
    vmForm.value.project_id = projects.value[0].id
    memberForm.value.project_id = projects.value[0].id
  }
}

const loadVMList = async () => {
  const params = {}
  if (filters.value.project_id) params.project_id = filters.value.project_id
  if (filters.value.keyword) params.keyword = filters.value.keyword
  const res = await getVMList(params)
  vmList.value = res.data || []
}

const loadTasks = async () => {
  const [myRes, pendingRes] = await Promise.all([getMyTasks(), getPendingTasks()])
  myTasks.value = myRes.data || []
  pendingTasks.value = pendingRes.data || []
}

const loadUsers = async () => {
  if (userStore.role !== 'admin') return
  const res = await getUsers()
  users.value = res.data || []
}

const loadAll = async () => {
  await Promise.all([loadProjects(), loadVMList(), loadTasks(), loadUsers()])
}

const openUserDialog = async () => { await loadUsers(); showUserDialog.value = true }
const openMemberDialog = async () => { await loadUsers(); showMemberDialog.value = true }

const handleCreateUser = async () => {
  if (!createUserForm.value.username || !createUserForm.value.password) {
    ElMessage.warning('请填写用户名和密码')
    return
  }
  await createUser(createUserForm.value)
  ElMessage.success('用户创建成功')
  createUserForm.value = { username: '', password: '' }
  await loadUsers()
}

const handleResetPassword = async () => {
  if (!resetPwdForm.value.username || !resetPwdForm.value.new_password) {
    ElMessage.warning('请填写用户名和新密码')
    return
  }
  await resetUserPassword(resetPwdForm.value)
  ElMessage.success('密码重置成功')
  resetPwdForm.value = { username: '', new_password: '' }
}

const selectVM = (vm) => { selectedVM.value = vm }

const handleCheck = async (vm) => {
  const res = await offlineCheck(vm.id)
  currentCheckVM.value = vm
  offlineResult.value = res.data
  ElMessage.success(`检查完成: ${res.data.result}`)
  await loadVMList()
}

const openOfflineDialog = (vm) => {
  offlineForm.value = {
    vm_id: vm.id, force_offline: false, force_reason: '', risk_ack: '',
    rollback_plan: '', data_migrated: false, dependency_cleared: false, stakeholders_notified: false
  }
  showOfflineDialog.value = true
}

const handleApplyOffline = async () => {
  await applyOffline(offlineForm.value)
  ElMessage.success('下线申请已提交')
  showOfflineDialog.value = false
  await loadTasks()
  await loadVMList()
}

const openDeleteDialog = (vm) => {
  deleteForm.value = { vm_id: vm.id, confirm_text: '', reason: '' }
  showDeleteDialog.value = true
}

const handleApplyDelete = async () => {
  await applyDelete(deleteForm.value)
  ElMessage.success('删除申请已提交')
  showDeleteDialog.value = false
  await loadTasks()
}

const approve = async (taskId, action) => {
  await approveTask(taskId, { action, comment: '' })
  ElMessage.success(action === 'approve' ? '审批通过' : '已驳回')
  await loadTasks()
  await loadVMList()
}

const handleAddVM = async () => {
  const required = ['project_id', 'vm_name', 'ip_address', 'ssh_user', 'ssh_password']
  const invalid = required.some(key => !vmForm.value[key])
  if (invalid) { ElMessage.warning('请补充必填项'); return }
  await addVM(vmForm.value)
  ElMessage.success('录入成功')
  showAddVM.value = false
  vmForm.value.vm_name = ''
  vmForm.value.ip_address = ''
  vmForm.value.ssh_user = ''
  vmForm.value.ssh_password = ''
  vmForm.value.remark = ''
  await loadVMList()
}

const handleCreateProject = async () => {
  if (!projectForm.value.project_name) { ElMessage.warning('项目名不能为空'); return }
  await createProject(projectForm.value)
  ElMessage.success('项目创建成功')
  showProjectDialog.value = false
  projectForm.value = { project_name: '', description: '' }
  await loadProjects()
}

const handleUpsertMember = async () => {
  if (!memberForm.value.project_id || !memberForm.value.username) {
    ElMessage.warning('请填写完整成员信息')
    return
  }
  const payload = { ...memberForm.value, username: String(memberForm.value.username).trim() }
  if (!payload.valid_until) payload.valid_until = null
  await upsertProjectMember(payload)
  ElMessage.success('成员配置成功')
  showMemberDialog.value = false
}

const handleExport = async () => {
  const params = {}
  if (filters.value.project_id) params.project_id = filters.value.project_id
  if (filters.value.keyword) params.keyword = filters.value.keyword
  const response = await exportVMs(params)
  const blob = new Blob([response.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `vm_export_${Date.now()}.xlsx`
  link.click()
  window.URL.revokeObjectURL(url)
}

const handleLogout = async () => {
  await userStore.logout()
  ElMessage.success('退出成功')
  router.push('/login')
}

onMounted(async () => {
  if (!userStore.token) { router.push('/login'); return }
  try { await loadAll() } catch (error) {
    ElMessage.error(error?.response?.data?.detail || error?.message || '加载失败')
  }
})
</script>

<style scoped>
/* 全局容器 */
.main-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #0a0e17 0%, #111827 50%, #0f172a 100%);
}

/* 头部导航 */
.header-wrap {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 64px;
  background: rgba(17, 24, 39, 0.9);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(0, 200, 255, 0.15);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #00d4ff;
}

.logo-text {
  font-size: 20px;
  font-weight: 600;
  color: #fff;
  letter-spacing: 1px;
}

.logo-text .highlight {
  color: #00d4ff;
  text-shadow: 0 0 10px rgba(0, 212, 255, 0.5);
}

.header-line {
  width: 1px;
  height: 24px;
  background: linear-gradient(to bottom, transparent, rgba(0, 200, 255, 0.3), transparent);
}

.version-text {
  color: rgba(255, 255, 255, 0.5) !important;
  font-size: 12px !important;
}

.header-center {
  display: flex;
  align-items: center;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 16px;
  background: rgba(0, 200, 255, 0.1);
  border: 1px solid rgba(0, 200, 255, 0.2);
  border-radius: 20px;
}

.user-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: linear-gradient(135deg, #00d4ff, #0088ff);
  border-radius: 50%;
  color: #fff;
}

.user-name {
  color: #fff;
  font-weight: 500;
}

.role-tag {
  font-size: 11px !important;
}

.header-right {
  display: flex;
  gap: 10px;
}

/* 科技感按钮 */
.tech-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: rgba(0, 200, 255, 0.1);
  border: 1px solid rgba(0, 200, 255, 0.3);
  border-radius: 8px;
  color: #00d4ff;
  font-size: 13px;
  transition: all 0.3s ease;
}

.tech-btn:hover {
  background: rgba(0, 200, 255, 0.2);
  border-color: #00d4ff;
  box-shadow: 0 0 15px rgba(0, 212, 255, 0.3);
}

.tech-btn.danger {
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.3);
  color: #ef4444;
}

.tech-btn.danger:hover {
  background: rgba(239, 68, 68, 0.2);
  border-color: #ef4444;
  box-shadow: 0 0 15px rgba(239, 68, 68, 0.3);
}

.tech-btn-primary {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 20px;
  background: linear-gradient(135deg, #00d4ff, #0088ff);
  border: none;
  border-radius: 8px;
  color: #fff;
  font-weight: 500;
  transition: all 0.3s ease;
}

.tech-btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 15px rgba(0, 212, 255, 0.4);
}

.tech-btn-success {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: linear-gradient(135deg, #10b981, #059669);
  border: none;
  border-radius: 8px;
  color: #fff;
  font-weight: 500;
  transition: all 0.3s ease;
}

.tech-btn-success:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 15px rgba(16, 185, 129, 0.4);
}

.tech-btn-export {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: linear-gradient(135deg, #8b5cf6, #7c3aed);
  border: none;
  border-radius: 8px;
  color: #fff;
  font-weight: 500;
  transition: all 0.3s ease;
}

.tech-btn-export:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 15px rgba(139, 92, 246, 0.4);
}

.tech-btn-mini {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: rgba(0, 200, 255, 0.1);
  border: 1px solid rgba(0, 200, 255, 0.2);
  border-radius: 6px;
  color: #00d4ff;
  font-size: 12px;
}

/* 主内容区 */
.main-wrap {
  padding: 20px 24px;
}

/* 筛选栏 */
.filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
}

.filter-left, .filter-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.tech-select {
  width: 180px;
}

.tech-select :deep(.el-input__wrapper) {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(0, 200, 255, 0.2);
  border-radius: 8px;
  box-shadow: none;
}

.tech-select :deep(.el-input__inner) {
  color: #fff;
}

.tech-input {
  width: 200px;
}

.tech-input :deep(.el-input__wrapper) {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(0, 200, 255, 0.2);
  border-radius: 8px;
  box-shadow: none;
}

.tech-input :deep(.el-input__inner) {
  color: #fff;
}

.tech-input :deep(.el-input__inner::placeholder) {
  color: rgba(255, 255, 255, 0.3);
}

/* 内容卡片 */
.content-card {
  background: rgba(17, 24, 39, 0.8);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(0, 200, 255, 0.15);
  border-radius: 12px;
  overflow: hidden;
  margin-bottom: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  background: rgba(0, 200, 255, 0.05);
  border-bottom: 1px solid rgba(0, 200, 255, 0.1);
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #fff;
  font-weight: 600;
  font-size: 14px;
}

.card-title .el-icon {
  color: #00d4ff;
}

.card-stats {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
}

.stat-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.stat-dot.running {
  background: #10b981;
  box-shadow: 0 0 8px #10b981;
}

.stat-dot.stopped {
  background: #ef4444;
  box-shadow: 0 0 8px #ef4444;
}

.stat-total {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
  padding-left: 12px;
  border-left: 1px solid rgba(255, 255, 255, 0.1);
}

/* 表格样式 */
.tech-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(0, 0, 0, 0.3);
  --el-table-row-hover-bg-color: rgba(0, 200, 255, 0.08);
  --el-table-border-color: rgba(0, 200, 255, 0.1);
  --el-table-text-color: rgba(255, 255, 255, 0.85);
  --el-table-header-text-color: rgba(255, 255, 255, 0.7);
}

.tech-table :deep(.el-table__header th) {
  background: rgba(0, 200, 255, 0.1) !important;
  font-weight: 600;
}

.tech-table :deep(.el-table__body td) {
  border-bottom: 1px solid rgba(0, 200, 255, 0.08);
}

.ip-text {
  font-family: 'Monaco', 'Consolas', monospace;
  color: #00d4ff;
}

.status-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.status-badge.running {
  background: rgba(16, 185, 129, 0.2);
  color: #10b981;
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.status-badge.stopped {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

/* 操作按钮 */
.action-buttons {
  display: flex;
  gap: 6px;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  transition: all 0.2s ease;
}

.action-btn.ssh {
  background: rgba(0, 200, 255, 0.15);
  border-color: rgba(0, 200, 255, 0.3);
  color: #00d4ff;
}

.action-btn.ssh:hover {
  background: rgba(0, 200, 255, 0.25);
  box-shadow: 0 0 10px rgba(0, 212, 255, 0.3);
}

.action-btn.check {
  background: rgba(139, 92, 246, 0.15);
  border-color: rgba(139, 92, 246, 0.3);
  color: #8b5cf6;
}

.action-btn.check:hover {
  background: rgba(139, 92, 246, 0.25);
  box-shadow: 0 0 10px rgba(139, 92, 246, 0.3);
}

.action-btn.offline {
  background: rgba(245, 158, 11, 0.15);
  border-color: rgba(245, 158, 11, 0.3);
  color: #f59e0b;
}

.action-btn.offline:hover {
  background: rgba(245, 158, 11, 0.25);
  box-shadow: 0 0 10px rgba(245, 158, 11, 0.3);
}

.action-btn.delete {
  background: rgba(239, 68, 68, 0.15);
  border-color: rgba(239, 68, 68, 0.3);
  color: #ef4444;
}

.action-btn.delete:hover {
  background: rgba(239, 68, 68, 0.25);
  box-shadow: 0 0 10px rgba(239, 68, 68, 0.3);
}

/* 底部面板 */
.bottom-panels {
  display: flex;
  gap: 16px;
}

.content-card.half {
  flex: 1;
}

.panel-content {
  padding: 16px;
  min-height: 200px;
}

.tech-desc :deep(.el-descriptions__label) {
  background: rgba(0, 0, 0, 0.2);
  color: rgba(255, 255, 255, 0.6);
  border-color: rgba(0, 200, 255, 0.1);
}

.tech-desc :deep(.el-descriptions__content) {
  background: rgba(0, 0, 0, 0.2);
  color: #fff;
  border-color: rgba(0, 200, 255, 0.1);
}

.text-success { color: #10b981; }
.text-danger { color: #ef4444; }
.text-warning { color: #f59e0b; }

.tech-tabs :deep(.el-tabs__item) {
  color: rgba(255, 255, 255, 0.6);
}

.tech-tabs :deep(.el-tabs__item.is-active) {
  color: #00d4ff;
}

.tech-tabs :deep(.el-tabs__active-bar) {
  background: #00d4ff;
}

.tech-table-mini {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(0, 0, 0, 0.3);
  --el-table-row-hover-bg-color: rgba(0, 200, 255, 0.08);
  --el-table-border-color: rgba(0, 200, 255, 0.1);
  --el-table-text-color: rgba(255, 255, 255, 0.85);
  --el-table-header-text-color: rgba(255, 255, 255, 0.7);
}

.state-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
}

.state-badge.pending {
  background: rgba(245, 158, 11, 0.2);
  color: #f59e0b;
}

.state-badge.approved {
  background: rgba(16, 185, 129, 0.2);
  color: #10b981;
}

.state-badge.rejected {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.mini-btn {
  padding: 3px 8px;
  font-size: 11px;
}

.mini-btn.pass {
  background: rgba(16, 185, 129, 0.2);
  border-color: rgba(16, 185, 129, 0.3);
  color: #10b981;
}

.mini-btn.reject {
  background: rgba(239, 68, 68, 0.2);
  border-color: rgba(239, 68, 68, 0.3);
  color: #ef4444;
}

/* SSH终端卡片 */
.terminal-card {
  margin-top: 16px;
}

/* 弹窗样式 */
.tech-dialog :deep(.el-dialog) {
  background: rgba(17, 24, 39, 0.95);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(0, 200, 255, 0.2);
  border-radius: 16px;
}

.tech-dialog :deep(.el-dialog__header) {
  border-bottom: 1px solid rgba(0, 200, 255, 0.1);
  padding: 16px 20px;
}

.tech-dialog :deep(.el-dialog__title) {
  color: #fff;
  font-weight: 600;
}

.tech-dialog :deep(.el-dialog__body) {
  padding: 20px;
}

.tech-form :deep(.el-form-item__label) {
  color: rgba(255, 255, 255, 0.7);
}

.tech-form :deep(.el-input__wrapper) {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(0, 200, 255, 0.2);
  border-radius: 8px;
  box-shadow: none;
}

.tech-form :deep(.el-input__inner) {
  color: #fff;
}

.tech-form :deep(.el-select .el-input__wrapper) {
  background: rgba(0, 0, 0, 0.3);
}

.tech-form :deep(.el-textarea__inner) {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(0, 200, 255, 0.2);
  color: #fff;
  border-radius: 8px;
}

.dialog-card {
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(0, 200, 255, 0.1);
  border-radius: 12px;
  padding: 16px;
}

.dialog-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #fff;
  font-weight: 600;
  margin-bottom: 16px;
}

.dialog-card-header .el-icon {
  color: #00d4ff;
}

.full-width {
  width: 100%;
  margin-top: 8px;
}

/* 响应式 */
@media (max-width: 1200px) {
  .bottom-panels {
    flex-direction: column;
  }
}

@media (max-width: 768px) {
  .header-wrap {
    flex-direction: column;
    height: auto;
    padding: 12px;
    gap: 12px;
  }

  .filter-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .filter-left, .filter-right {
    flex-wrap: wrap;
    justify-content: center;
  }
}
</style>
