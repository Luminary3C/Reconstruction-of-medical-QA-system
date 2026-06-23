<script setup lang="ts">
import { ref } from 'vue';
import { useChatStore } from '@/stores/chat';
import BackendSwitch from '@/components/backend-switch.vue';
import LoginBar from '@/components/login-bar.vue';
import SessionList from '@/components/session-list.vue';
import ChatWindow from '@/components/chat-window.vue';
import KnowledgePanel from '@/components/knowledge-panel.vue';

const store = useChatStore();

type ViewTab = 'chat' | 'knowledge';
const currentView = ref<ViewTab>('chat');

const tabs: { key: ViewTab; label: string }[] = [
  { key: 'chat', label: '对话' },
  { key: 'knowledge', label: '知识库' },
];
</script>

<template>
  <div class="app-root">
    <header class="top-bar">
      <span class="brand">医疗问答系统</span>
      <nav class="nav-tabs">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          class="nav-tab"
          :class="{ active: currentView === tab.key }"
          @click="currentView = tab.key"
        >
          {{ tab.label }}
        </button>
      </nav>
      <BackendSwitch />
      <LoginBar v-if="store.backend === 'java'" />
    </header>
    <div class="body-area">
      <template v-if="currentView === 'chat'">
        <SessionList />
        <div class="main-column">
          <ChatWindow />
        </div>
      </template>
      <KnowledgePanel v-else />
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
  font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
  background: #f0f4f8;
  color: #1e293b;
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
  background: #ffffff;
  border-bottom: 1px solid #dde4ed;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.brand {
  padding: 0 20px;
  font-weight: 700;
  font-size: 16px;
  color: #2c6fce;
  white-space: nowrap;
}
.nav-tabs {
  display: flex;
  gap: 4px;
  padding: 0 16px;
}
.nav-tab {
  padding: 8px 18px;
  border: none;
  border-radius: 6px 6px 0 0;
  background: transparent;
  color: #64748b;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}
.nav-tab:hover { color: #2c6fce; background: #f0f4f8; }
.nav-tab.active {
  color: #2c6fce;
  font-weight: 600;
  border-bottom: 2px solid #2c6fce;
}
.body-area {
  flex: 1;
  display: flex;
  overflow: hidden;
}
.main-column {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
</style>
