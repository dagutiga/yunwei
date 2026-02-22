<template>
  <el-container style="height: 100vh;">
    <el-header>
      <el-row justify="space-between" align="middle">
        <el-text size="large" bold>虚拟机管理系统</el-text>
        <el-button @click="handleLogout" type="primary" plain>退出登录</el-button>
      </el-row>
    </el-header>
    <el-container>
      <el-aside width="300px">
        <el-card>
          <el-button @click="showAddVM = true" type="primary" style="width: 100%; margin-bottom: 10px;">
            录入虚拟机
          </el-button>
          <el-list border>
            <el-list-item 
              v-for="vm in vmList" 
              :key="vm.id"
              @click="selectVM(vm)"
              :class="{ active: selectedVM?.id === vm.id }"
            >
              <el-text>{{ vm.vm_name }} ({{ vm.ip_address }})</el-text>
            </el-list-item>
          </el-list>
        </el-card>
      </el-aside>
      <el-main>
        <el-card v-if="selectedVM">
          <template #header>
            <el-text bold>{{ selectedVM.vm_name }} - SSH终端</el-text>
          </template>
          <SSHTerminal :vm-id="selectedVM.id" />
        </el-card>
        <el-empty v-else description="请选择左侧的虚拟机"></el-empty>
      </el-main>
    </el-container>
  </el-container>

  <!-- 录入虚拟机弹窗 -->
  <el-dialog v-model="showAddVM" title="录入虚拟机信息" width="500px">
    <el-form :model="vmForm" label-width="100px">
      <el-form-item label="虚拟机名称" required>
        <el-input v-model="vmForm.vm_name"></el-input>
      </el-form-item>
      <el-form-item label="IP地址" required>
        <el-input v-model="vmForm.ip_address"></el-input>
      </el-form-item>
      <el-form-item label="SSH端口">
        <el-input-number v-model="vmForm.ssh_port" :min="1" :max="65535" :default-value="22"></el-input-number>
      </el-form-item>
      <el-form-item label="SSH用户名" required>
        <el-input v-model="vmForm.ssh_user"></el-input>
      </el-form-item>
      <el-form-item label="SSH密码" required>
        <el-input v-model="vmForm.ssh_password" type="password"></el-input>
      </el-form-item>
      <el-form-item label="操作系统">
        <el-select v-model="vmForm.os_type">
          <el-option label="Linux" value="Linux"></el-option>
          <el-option label="Windows" value="Windows"></el-option>
        </el-select>
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="vmForm.remark" type="textarea"></el-input>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showAddVM = false">取消</el-button>
      <el-button @click="handleAddVM" type="primary">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/store/user'
import { getVMList, addVM } from '@/api/vm'
import SSHTerminal from '@/components/SSHTerminal.vue'

const router = useRouter()
const userStore = useUserStore()

// 状态定义
const vmList = ref([])
const selectedVM = ref(null)
const showAddVM = ref(false)
const vmForm = ref({
  vm_name: '',
  ip_address: '',
  ssh_port: 22,
  ssh_user: '',
  ssh_password: '',
  os_type: 'Linux',
  remark: ''
})

// 加载虚拟机列表
const loadVMList = async () => {
  const res = await getVMList()
  vmList.value = res.data
}

// 选择虚拟机
const selectVM = (vm) => {
  selectedVM.value = vm
}

// 录入虚拟机
const handleAddVM = async () => {
  const { vm_name, ip_address, ssh_user } = vmForm.value
  if (!vm_name || !ip_address || !ssh_user) {
    ElMessage.warning('名称、IP、用户名不能为空')
    return
  }
  await addVM(vmForm.value)
  ElMessage.success('录入成功')
  showAddVM.value = false
  loadVMList()
  // 重置表单
  vmForm.value = {
    vm_name: '',
    ip_address: '',
    ssh_port: 22,
    ssh_user: '',
    ssh_password: '',
    os_type: 'Linux',
    remark: ''
  }
}

// 退出登录
const handleLogout = async () => {
  await userStore.logout()
  ElMessage.success('退出成功')
  router.push('/login')
}

// 初始化
onMounted(() => {
  if (!userStore.token) {
    router.push('/login')
    return
  }
  loadVMList()
})
</script>

<style scoped>
.active {
  background-color: #e6f7ff;
}
.el-header {
  background-color: #fff;
  border-bottom: 1px solid #e6e6e6;
  padding: 0 20px;
}
</style>
