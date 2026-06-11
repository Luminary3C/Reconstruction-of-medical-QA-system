<script setup lang="ts">
import { useChatStore } from '@/stores/chat';
import BackendSwitch from '@/components/backend-switch.vue';
import LoginBar from '@/components/login-bar.vue';
import SessionList from '@/components/session-list.vue';
import ChatWindow from '@/components/chat-window.vue';

const store = useChatStore();
</script>

<template>
  <div class="app-root">
    <header class="top-bar">
      <span class="brand">RAG Chat</span>
      <BackendSwitch />
      <LoginBar v-if="store.backend === 'java'" />
    </header>
    <div class="body-area">
      <SessionList />
      <ChatWindow />
    </div>
  </div>
</template>

<style>
*,
*::before,
*::after {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
html, body, #app {
  height: 100%;
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
  background: #1a1a2e;
  color: #eee;
}
</style>

<style scoped>
.app-root {
  height: 100%;
  display: flex;
  flex-direction: column;
}
.top-bar {
  display: flex;
  align-items: center;
  background: #16213e;
  border-bottom: 1px solid #333;
}
.brand {
  padding: 0 16px;
  font-weight: 700;
  font-size: 16px;
  color: #4ecdc4;
}
.body-area {
  flex: 1;
  display: flex;
  overflow: hidden;
}
</style>
