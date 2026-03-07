<template>
  <div class="login-container">
    <!-- 动态背景 -->
    <div class="bg-grid"></div>
    <div class="bg-glow bg-glow-1"></div>
    <div class="bg-glow bg-glow-2"></div>
    <div class="bg-particles">
      <span v-for="i in 20" :key="i" class="particle" :style="getParticleStyle(i)"></span>
    </div>

    <el-card class="login-card">
      <div class="card-glow"></div>
      <div class="login-header">
        <div class="logo-icon">
          <el-icon :size="40"><Monitor /></el-icon>
        </div>
        <h1 class="title">云威虚拟机管理平台</h1>
        <p class="subtitle">Cloud Infrastructure Management</p>
      </div>

      <el-form :model="loginForm" class="login-form" @keyup.enter="handleLogin">
        <el-form-item>
          <el-input
            v-model="loginForm.username"
            placeholder="请输入用户名"
            size="large"
            :prefix-icon="User"
            class="tech-input"
          />
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            size="large"
            :prefix-icon="Lock"
            class="tech-input"
            show-password
          />
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            @click="handleLogin"
            class="tech-button"
            :loading="loading"
          >
            <span v-if="!loading">立即登录</span>
            <span v-else>登录中...</span>
          </el-button>
        </el-form-item>
      </el-form>

      <div class="login-footer">
        <span class="version">v1.1.0</span>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Monitor, User, Lock } from '@element-plus/icons-vue'
import { useUserStore } from '@/store/user'

const router = useRouter()
const userStore = useUserStore()
const loading = ref(false)

const loginForm = ref({
  username: '',
  password: ''
})

const getParticleStyle = (i) => {
  const random = (min, max) => Math.random() * (max - min) + min
  return {
    left: `${random(0, 100)}%`,
    animationDelay: `${random(0, 5)}s`,
    animationDuration: `${random(3, 8)}s`,
    width: `${random(2, 6)}px`,
    height: `${random(2, 6)}px`,
    opacity: random(0.1, 0.5)
  }
}

const handleLogin = async () => {
  if (!loginForm.value.username || !loginForm.value.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    await userStore.login(loginForm.value)
    ElMessage.success({ message: '登录成功，欢迎回来！', duration: 1500 })
    router.push('/main')
  } catch (e) {
    ElMessage.error('登录失败，请检查账号密码')
    console.error('登录失败:', e)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  overflow: hidden;
  background: linear-gradient(135deg, #0a0e17 0%, #1a1f35 50%, #0d1520 100%);
}

/* 网格背景 */
.bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(0, 255, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 255, 255, 0.03) 1px, transparent 1px);
  background-size: 50px 50px;
  animation: gridMove 20s linear infinite;
}

@keyframes gridMove {
  0% { transform: translate(0, 0); }
  100% { transform: translate(50px, 50px); }
}

/* 动态光晕 */
.bg-glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(100px);
  opacity: 0.4;
}

.bg-glow-1 {
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, rgba(0, 200, 255, 0.3), transparent 70%);
  top: -200px;
  right: -100px;
  animation: glowPulse 8s ease-in-out infinite;
}

.bg-glow-2 {
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, rgba(138, 43, 226, 0.3), transparent 70%);
  bottom: -150px;
  left: -100px;
  animation: glowPulse 10s ease-in-out infinite reverse;
}

@keyframes glowPulse {
  0%, 100% { transform: scale(1); opacity: 0.4; }
  50% { transform: scale(1.1); opacity: 0.6; }
}

/* 粒子效果 */
.bg-particles {
  position: absolute;
  inset: 0;
  overflow: hidden;
}

.particle {
  position: absolute;
  bottom: -10px;
  background: linear-gradient(45deg, #00ffff, #0088ff);
  border-radius: 50%;
  animation: particleRise linear infinite;
}

@keyframes particleRise {
  0% {
    transform: translateY(0) scale(1);
    opacity: 0;
  }
  10% {
    opacity: var(--opacity, 0.5);
  }
  90% {
    opacity: var(--opacity, 0.5);
  }
  100% {
    transform: translateY(-100vh) scale(0);
    opacity: 0;
  }
}

/* 登录卡片 */
.login-card {
  position: relative;
  width: 420px;
  background: rgba(20, 25, 40, 0.85);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(0, 200, 255, 0.2);
  border-radius: 16px;
  box-shadow:
    0 0 40px rgba(0, 200, 255, 0.1),
    0 25px 50px rgba(0, 0, 0, 0.5),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
  overflow: hidden;
}

.card-glow {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, #00d4ff, #8a2be2, #00d4ff, transparent);
  background-size: 200% 100%;
  animation: borderGlow 3s linear infinite;
}

@keyframes borderGlow {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.login-header {
  text-align: center;
  padding: 30px 0 20px;
}

.logo-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 80px;
  height: 80px;
  margin-bottom: 16px;
  background: linear-gradient(135deg, rgba(0, 200, 255, 0.2), rgba(138, 43, 226, 0.2));
  border-radius: 20px;
  color: #00d4ff;
  box-shadow:
    0 0 30px rgba(0, 212, 255, 0.3),
    inset 0 0 20px rgba(0, 212, 255, 0.1);
  animation: iconPulse 3s ease-in-out infinite;
}

@keyframes iconPulse {
  0%, 100% { box-shadow: 0 0 30px rgba(0, 212, 255, 0.3), inset 0 0 20px rgba(0, 212, 255, 0.1); }
  50% { box-shadow: 0 0 50px rgba(0, 212, 255, 0.5), inset 0 0 30px rgba(0, 212, 255, 0.2); }
}

.title {
  font-size: 24px;
  font-weight: 600;
  color: #fff;
  margin: 0 0 8px;
  letter-spacing: 2px;
  text-shadow: 0 0 20px rgba(0, 212, 255, 0.5);
}

.subtitle {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
  margin: 0;
  letter-spacing: 1px;
  text-transform: uppercase;
}

.login-form {
  padding: 0 30px 30px;
}

.login-form :deep(.el-input__wrapper) {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(0, 200, 255, 0.2);
  border-radius: 10px;
  box-shadow: none;
  padding: 4px 12px;
  transition: all 0.3s ease;
}

.login-form :deep(.el-input__wrapper:hover) {
  border-color: rgba(0, 200, 255, 0.4);
}

.login-form :deep(.el-input__wrapper.is-focus) {
  border-color: #00d4ff;
  box-shadow: 0 0 15px rgba(0, 212, 255, 0.3);
}

.login-form :deep(.el-input__inner) {
  color: #fff;
  height: 40px;
}

.login-form :deep(.el-input__inner::placeholder) {
  color: rgba(255, 255, 255, 0.3);
}

.login-form :deep(.el-input__prefix) {
  color: rgba(0, 200, 255, 0.6);
}

.tech-button {
  width: 100%;
  height: 48px;
  font-size: 16px;
  font-weight: 500;
  letter-spacing: 2px;
  background: linear-gradient(135deg, #00d4ff 0%, #0088ff 50%, #8a2be2 100%);
  background-size: 200% 200%;
  border: none;
  border-radius: 10px;
  color: #fff;
  cursor: pointer;
  transition: all 0.3s ease;
  animation: buttonGradient 4s ease infinite;
}

@keyframes buttonGradient {
  0%, 100% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
}

.tech-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 30px rgba(0, 212, 255, 0.4);
}

.tech-button:active {
  transform: translateY(0);
}

.login-footer {
  text-align: center;
  padding: 0 0 20px;
}

.version {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.3);
  letter-spacing: 1px;
}

/* 响应式 */
@media (max-width: 480px) {
  .login-card {
    width: 90%;
    margin: 20px;
  }

  .title {
    font-size: 20px;
  }
}
</style>
