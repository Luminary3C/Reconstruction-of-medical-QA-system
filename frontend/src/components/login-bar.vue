<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import { login } from '@/api/chat-java';
import { useChatStore } from '@/stores/chat';

const store = useChatStore();

function onAuthExpired() {
  store.setJavaLoggedIn(false);
  store.setJavaUserId('');
}
onMounted(() => window.addEventListener('auth:expired', onAuthExpired));
onUnmounted(() => window.removeEventListener('auth:expired', onAuthExpired));

const username = ref('');
const password = ref('');
const error = ref('');
const loading = ref(false);

onMounted(() => {
  const savedUsername = localStorage.getItem('jwt-username');
  const token = localStorage.getItem('jwt-token');
  if (token && savedUsername) {
    store.setJavaLoggedIn(true);
    store.setJavaUserId(savedUsername);
  }
});

async function handleLogin() {
  error.value = '';
  loading.value = true;
  try {
    const res = await login({ username: username.value, password: password.value });
    localStorage.setItem('jwt-token', res.token);
    localStorage.setItem('jwt-username', res.username);
    store.setJavaLoggedIn(true);
    store.setJavaUserId(res.username);
    username.value = '';
    password.value = '';
  } catch (err) {
    error.value = err instanceof Error ? err.message : '登录失败';
  } finally {
    loading.value = false;
  }
}

function handleLogout() {
  localStorage.removeItem('jwt-token');
  localStorage.removeItem('jwt-username');
  store.setJavaLoggedIn(false);
  store.setJavaUserId('');
}
</script>

<template>
  <div class="login-bar">
    <template v-if="store.javaLoggedIn">
      <span class="login-status">已登录：<strong>{{ store.javaUserId }}</strong></span>
      <span v-if="store.isRoot" class="admin-badge">管理员</span>
      <button class="login-btn logout" @click="handleLogout">退出</button>
    </template>
    <template v-else>
      <input
        v-model="username"
        class="login-input"
        placeholder="用户名"
        :disabled="loading"
      />
      <input
        v-model="password"
        class="login-input"
        type="password"
        placeholder="密码"
        :disabled="loading"
        @keydown.enter="handleLogin"
      />
      <button class="login-btn" :disabled="loading" @click="handleLogin">
        {{ loading ? '...' : '登录' }}
      </button>
      <span v-if="error" class="login-error">{{ error }}</span>
    </template>
  </div>
</template>

<style scoped>
.login-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 16px;
  background: #f8fafc;
  border-bottom: 1px solid #dde4ed;
  flex: 1;
  justify-content: flex-end;
}
.login-status {
  color: #475569;
  font-size: 13px;
}
.login-status strong {
  color: #2c6fce;
}
.admin-badge {
  background: #0ea882;
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 10px;
  text-transform: uppercase;
}
.login-input {
  padding: 6px 10px;
  border: 1px solid #d0d7e0;
  border-radius: 6px;
  background: #fff;
  color: #1e293b;
  font-size: 13px;
  width: 130px;
  outline: none;
  transition: border-color 0.15s;
}
.login-input:focus { border-color: #2c6fce; }
.login-btn {
  padding: 6px 14px;
  border: none;
  border-radius: 6px;
  background: #2c6fce;
  color: #fff;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}
.login-btn.logout {
  background: #e8edf2;
  color: #64748b;
}
.login-btn:hover:not(:disabled) { background: #1a5ab8; }
.login-btn.logout:hover { background: #dde4ed; color: #475569; }
.login-error {
  color: #e74c3c;
  font-size: 12px;
}
</style>
