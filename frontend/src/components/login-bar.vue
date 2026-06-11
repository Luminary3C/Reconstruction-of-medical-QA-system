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

// 页面加载时检查是否有已保存的 token 和用户名
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
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'login failed';
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
      <span class="login-status">Logged in as {{ store.javaUserId }}</span>
      <button class="login-btn logout" @click="handleLogout">Logout</button>
    </template>
    <template v-else>
      <input
        v-model="username"
        class="login-input"
        placeholder="Username"
        :disabled="loading"
      />
      <input
        v-model="password"
        class="login-input"
        type="password"
        placeholder="Password"
        :disabled="loading"
        @keydown.enter="handleLogin"
      />
      <button class="login-btn" :disabled="loading" @click="handleLogin">
        {{ loading ? '...' : 'Login' }}
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
  background: #0f3460;
  border-bottom: 1px solid #1a508b;
}
.login-status {
  color: #4ecdc4;
  font-size: 13px;
}
.login-input {
  padding: 4px 8px;
  border: 1px solid #444;
  border-radius: 4px;
  background: #1a1a2e;
  color: #eee;
  font-size: 13px;
  width: 120px;
  outline: none;
}
.login-btn {
  padding: 4px 12px;
  border: none;
  border-radius: 4px;
  background: #e94560;
  color: #fff;
  font-size: 13px;
  cursor: pointer;
}
.login-btn.logout {
  background: #444;
}
.login-btn:hover:not(:disabled) {
  opacity: 0.85;
}
.login-error {
  color: #ff6b6b;
  font-size: 12px;
}
</style>
