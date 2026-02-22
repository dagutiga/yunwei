<template>
  <div class="login-container">
    <el-card class="login-card">
      <template #header>
        <el-text size="large" bold>虚拟机管理系统</el-text>
      </template>
      <el-form :model="loginForm" label-width="80px" class="login-form">
        <el-form-item label="用户名" required>
          <el-input v-model="loginForm.username" placeholder="请输入用户名"></el-input>
        </el-form-item>
        <el-form-item label="密码" required>
          <el-input v-model="loginForm.password" type="password" placeholder="请输入密码"></el-input>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleLogin" style="width: 100%;">登录</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/store/user'

const router = useRouter()
const userStore = useUserStore()

const loginForm = ref({
  username: '',
  password: ''
})

const handleLogin = async () => {
  if (!loginForm.value.username || !loginForm.value.password) {
    ElMessage.warning('用户名和密码不能为空')
    return
  }
  try {
    await userStore.login(loginForm.value)
    ElMessage.success('登录成功')
    router.push('/main')
  } catch (e) {
    ElMessage.error('登录失败，请检查账号密码')
    console.error('登录失败:', e)
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: #f5f5f5;
}
.login-card {
  width: 400px;
  padding: 20px;
}
.login-form {
  margin-top: 20px;
}
</style>
