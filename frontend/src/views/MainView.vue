<template>
  <el-container style="height: 100vh;">
    <el-header class="header-wrap">
      <el-row justify="space-between" align="middle">
        <el-space>
          <el-text size="large" tag="b">虚拟机自助管理 V1.1</el-text>
          <el-tag type="info">{{ userStore.username || '-' }}</el-tag>
          <el-tag :type="userStore.role === 'admin' ? 'danger' : 'success'">{{ userStore.role || 'user' }}</el-tag>
        </el-space>
        <el-space>
          <el-button @click="loadAll" plain>刷新</el-button>
          <el-button v-if="userStore.role === 'admin'" @click="openUserDialog" plain>用户管理</el-button>
          <el-button @click="handleLogout" type="primary" plain>退出登录</el-button>
        </el-space>
      </el-row>
    </el-header>

    <el-main class="main-wrap">
      <el-card>
        <el-row :gutter="12" align="middle">
          <el-col :span="6">
            <el-select v-model="filters.project_id" placeholder="选择项目" clearable style="width: 100%;" @change="loadVMList">
              <el-option v-for="item in projects" :key="item.id" :label="item.project_name" :value="item.id" />
            </el-select>
          </el-col>
          <el-col :span="6">
            <el-input v-model="filters.keyword" placeholder="搜索 VM/IP/项目" clearable @keyup.enter="loadVMList" />
          </el-col>
          <el-col :span="12" class="right-actions">
            <el-space wrap>
              <el-button type="primary" @click="loadVMList">查询</el-button>
              <el-button @click="showAddVM = true">录入虚拟机</el-button>
              <el-button v-if="canManageProject" @click="openMemberDialog">项目成员配置</el-button>
              <el-button v-if="userStore.role === 'admin'" @click="showProjectDialog = true">创建项目</el-button>
              <el-button v-if="canExport" type="success" @click="handleExport">导出 Excel</el-button>
            </el-space>
          </el-col>
        </el-row>
      </el-card>

      <el-card style="margin-top: 12px;">
        <el-table :data="vmList" border style="width: 100%;" height="320">
          <el-table-column prop="id" label="ID" width="70" />
          <el-table-column prop="project_name" label="项目" width="130" />
          <el-table-column prop="vm_name" label="VM名称" min-width="130" />
          <el-table-column prop="ip_address" label="IP" width="140" />
          <el-table-column prop="environment" label="环境" width="90" />
          <el-table-column prop="power_state" label="运行状态" width="100" />
          <el-table-column prop="offline_status" label="下线状态" width="130" />
          <el-table-column prop="offline_check_result" label="检查结果" width="100" />
          <el-table-column label="操作" fixed="right" width="360">
            <template #default="scope">
              <el-space wrap>
                <el-button size="small" @click="selectVM(scope.row)">SSH</el-button>
                <el-button size="small" @click="handleCheck(scope.row)">下线检查</el-button>
                <el-button size="small" type="warning" @click="openOfflineDialog(scope.row)">申请下线</el-button>
                <el-button size="small" type="danger" @click="openDeleteDialog(scope.row)">申请删除</el-button>
              </el-space>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-row :gutter="12" style="margin-top: 12px;">
        <el-col :span="12">
          <el-card>
            <template #header>
              <el-row justify="space-between" align="middle">
                <el-text tag="b">下线检查详情</el-text>
                <el-tag>{{ offlineResult?.result || '-' }}</el-tag>
              </el-row>
            </template>
            <el-descriptions v-if="currentCheckVM" :column="1" border size="small">
              <el-descriptions-item label="VM">{{ currentCheckVM.vm_name }}</el-descriptions-item>
              <el-descriptions-item label="L1阻断">
                <span v-if="!offlineResult?.l1?.length">无</span>
                <span v-else>{{ offlineResult.l1.map(i => i.title).join('；') }}</span>
              </el-descriptions-item>
              <el-descriptions-item label="L2风险">
                <span v-if="!offlineResult?.l2?.length">无</span>
                <span v-else>{{ offlineResult.l2.map(i => i.title).join('；') }}</span>
              </el-descriptions-item>
              <el-descriptions-item label="L3人工确认">
                {{ offlineResult?.l3?.map(i => i.title).join('；') || '-' }}
              </el-descriptions-item>
            </el-descriptions>
            <el-empty v-else description="请先执行下线检查" />
          </el-card>
        </el-col>

        <el-col :span="12">
          <el-card>
            <template #header>
              <el-row justify="space-between" align="middle">
                <el-text tag="b">审批中心</el-text>
                <el-space>
                  <el-button size="small" @click="loadTasks">刷新</el-button>
                </el-space>
              </el-row>
            </template>
            <el-tabs>
              <el-tab-pane label="我的申请">
                <el-table :data="myTasks" border size="small" height="190">
                  <el-table-column prop="id" label="ID" width="60" />
                  <el-table-column prop="task_type" label="类型" width="90" />
                  <el-table-column prop="vm_name" label="VM" min-width="120" />
                  <el-table-column prop="state" label="状态" min-width="130" />
                </el-table>
              </el-tab-pane>
              <el-tab-pane label="待审批">
                <el-table :data="pendingTasks" border size="small" height="190">
                  <el-table-column prop="id" label="ID" width="60" />
                  <el-table-column prop="task_type" label="类型" width="90" />
                  <el-table-column prop="vm_name" label="VM" min-width="110" />
                  <el-table-column prop="requester" label="发起人" width="100" />
                  <el-table-column label="操作" width="160">
                    <template #default="scope">
                      <el-space>
                        <el-button size="small" type="success" @click="approve(scope.row.id, 'approve')">通过</el-button>
                        <el-button size="small" type="danger" @click="approve(scope.row.id, 'reject')">驳回</el-button>
                      </el-space>
                    </template>
                  </el-table-column>
                </el-table>
              </el-tab-pane>
            </el-tabs>
          </el-card>
        </el-col>
      </el-row>

      <el-card v-if="selectedVM" style="margin-top: 12px;">
        <template #header>
          <el-text tag="b">{{ selectedVM.vm_name }} - SSH终端</el-text>
        </template>
        <SSHTerminal :vm-id="selectedVM.id" />
      </el-card>
    </el-main>
  </el-container>

  <el-dialog v-model="showAddVM" title="录入虚拟机" width="560px">
    <el-form :model="vmForm" label-width="100px">
      <el-form-item label="所属项目" required>
        <el-select v-model="vmForm.project_id" style="width: 100%;">
          <el-option v-for="item in projects" :key="item.id" :label="item.project_name" :value="item.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="VM名称" required><el-input v-model="vmForm.vm_name" /></el-form-item>
      <el-form-item label="IP" required><el-input v-model="vmForm.ip_address" /></el-form-item>
      <el-form-item label="环境"><el-select v-model="vmForm.environment" style="width: 100%;"><el-option label="prod" value="prod" /><el-option label="staging" value="staging" /><el-option label="dev" value="dev" /></el-select></el-form-item>
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

  <el-dialog v-model="showOfflineDialog" title="申请下线" width="620px">
    <el-form :model="offlineForm" label-width="120px">
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

  <el-dialog v-model="showDeleteDialog" title="申请删除（不可逆）" width="520px">
    <el-alert title="请确认删除前已经通过下线检查。" type="warning" show-icon :closable="false" />
    <el-form :model="deleteForm" label-width="110px" style="margin-top: 10px;">
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

  <el-dialog v-model="showProjectDialog" title="创建项目" width="480px">
    <el-form :model="projectForm" label-width="90px">
      <el-form-item label="项目名" required><el-input v-model="projectForm.project_name" /></el-form-item>
      <el-form-item label="描述"><el-input v-model="projectForm.description" type="textarea" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showProjectDialog = false">取消</el-button>
      <el-button type="primary" @click="handleCreateProject">创建</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="showMemberDialog" title="项目成员配置" width="520px">
    <el-form :model="memberForm" label-width="90px">
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

  <el-dialog v-model="showUserDialog" title="用户管理（管理员）" width="680px">
    <el-row :gutter="12">
      <el-col :span="12">
        <el-card shadow="never">
          <template #header><el-text tag="b">创建普通用户</el-text></template>
          <el-form :model="createUserForm" label-width="90px">
            <el-form-item label="用户名" required><el-input v-model="createUserForm.username" /></el-form-item>
            <el-form-item label="密码" required><el-input v-model="createUserForm.password" type="password" show-password /></el-form-item>
          </el-form>
          <el-button type="primary" @click="handleCreateUser">创建用户</el-button>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never">
          <template #header><el-text tag="b">重置用户密码</el-text></template>
          <el-form :model="resetPwdForm" label-width="90px">
            <el-form-item label="用户名" required><el-input v-model="resetPwdForm.username" /></el-form-item>
            <el-form-item label="新密码" required><el-input v-model="resetPwdForm.new_password" type="password" show-password /></el-form-item>
          </el-form>
          <el-button type="warning" @click="handleResetPassword">重置密码</el-button>
        </el-card>
      </el-col>
    </el-row>

    <el-divider />
    <el-table :data="users" border size="small" height="220">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="username" label="用户名" min-width="150" />
      <el-table-column prop="create_time" label="创建时间" min-width="180" />
    </el-table>
  </el-dialog>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/store/user'
import { createUser, getUsers, resetUserPassword } from '@/api/user'
import {
  addVM,
  applyDelete,
  applyOffline,
  approveTask,
  createProject,
  exportVMs,
  getMyTasks,
  getPendingTasks,
  getProjects,
  getVMList,
  offlineCheck,
  upsertProjectMember
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
  project_id: null,
  vm_name: '',
  ip_address: '',
  ssh_port: 22,
  ssh_user: '',
  ssh_password: '',
  os_type: 'Linux',
  environment: 'prod',
  owner_name: '',
  cpu_cores: 2,
  memory_gb: 4,
  disk_gb: 50,
  remark: ''
})

const offlineForm = ref({
  vm_id: null,
  force_offline: false,
  force_reason: '',
  risk_ack: '',
  rollback_plan: '',
  data_migrated: false,
  dependency_cleared: false,
  stakeholders_notified: false
})

const deleteForm = ref({
  vm_id: null,
  confirm_text: '',
  reason: ''
})

const projectForm = ref({
  project_name: '',
  description: ''
})

const memberForm = ref({
  project_id: null,
  username: '',
  role: 'member',
  valid_until: ''
})

const currentProjectRole = computed(() => {
  const projectId = filters.value.project_id
  if (!projectId) return ''
  const target = projects.value.find(item => item.id === projectId)
  return target?.role || ''
})

const canManageProject = computed(() => userStore.role === 'admin' || currentProjectRole.value === 'owner')
const canExport = computed(() => userStore.role === 'admin' || currentProjectRole.value === 'owner')

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

const openUserDialog = async () => {
  await loadUsers()
  showUserDialog.value = true
}

const openMemberDialog = async () => {
  await loadUsers()
  showMemberDialog.value = true
}

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

const selectVM = (vm) => {
  selectedVM.value = vm
}

const handleCheck = async (vm) => {
  const res = await offlineCheck(vm.id)
  currentCheckVM.value = vm
  offlineResult.value = res.data
  ElMessage.success(`检查完成: ${res.data.result}`)
  await loadVMList()
}

const openOfflineDialog = (vm) => {
  offlineForm.value = {
    vm_id: vm.id,
    force_offline: false,
    force_reason: '',
    risk_ack: '',
    rollback_plan: '',
    data_migrated: false,
    dependency_cleared: false,
    stakeholders_notified: false
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
  deleteForm.value = {
    vm_id: vm.id,
    confirm_text: '',
    reason: ''
  }
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
  if (invalid) {
    ElMessage.warning('请补充必填项')
    return
  }
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
  if (!projectForm.value.project_name) {
    ElMessage.warning('项目名不能为空')
    return
  }
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
  const payload = {
    ...memberForm.value,
    username: String(memberForm.value.username).trim()
  }
  if (!payload.valid_until) {
    payload.valid_until = null
  }
  await upsertProjectMember(payload)
  ElMessage.success('成员配置成功')
  showMemberDialog.value = false
}

const handleExport = async () => {
  const params = {}
  if (filters.value.project_id) params.project_id = filters.value.project_id
  if (filters.value.keyword) params.keyword = filters.value.keyword
  const response = await exportVMs(params)
  const blob = new Blob([response.data], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
  })
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
  if (!userStore.token) {
    router.push('/login')
    return
  }
  try {
    await loadAll()
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || error?.message || '加载失败')
  }
})
</script>

<style scoped>
.header-wrap {
  background: #fff;
  border-bottom: 1px solid #ececec;
  padding: 0 16px;
}

.main-wrap {
  background: #f5f7fa;
}

.right-actions {
  text-align: right;
}
</style>
