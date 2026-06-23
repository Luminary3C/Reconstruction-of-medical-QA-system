<script setup lang="ts">
import { useChatStore } from '@/stores/chat';

const store = useChatStore();
</script>

<template>
  <aside class="session-list">
    <button class="new-chat-btn" @click="store.createSession()">+ 新建对话</button>
    <ul class="sessions">
      <li
        v-for="s in store.sessions"
        :key="s.id"
        class="session-item"
        :class="{ active: s.id === store.currentSessionId }"
        @click="store.selectSession(s.id)"
      >
        <span class="session-title">{{ s.title }}</span>
        <span class="session-time">{{ new Date(s.createdAt).toLocaleTimeString() }}</span>
      </li>
    </ul>
  </aside>
</template>

<style scoped>
.session-list {
  width: 240px;
  background: #e8edf2;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #dde4ed;
  overflow: hidden;
}
.new-chat-btn {
  margin: 14px;
  padding: 10px;
  border: none;
  border-radius: 8px;
  background: #2c6fce;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}
.new-chat-btn:hover { background: #1a5ab8; }
.sessions {
  list-style: none;
  margin: 0;
  padding: 0;
  overflow-y: auto;
  flex: 1;
}
.session-item {
  padding: 12px 16px;
  cursor: pointer;
  border-bottom: 1px solid #dde4ed;
  display: flex;
  flex-direction: column;
  gap: 4px;
  transition: background 0.1s;
}
.session-item:hover { background: #f8fafc; }
.session-item.active {
  background: #ffffff;
  border-right: 3px solid #2c6fce;
}
.session-title {
  font-size: 13px;
  font-weight: 500;
  color: #1e293b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.session-item.active .session-title { color: #2c6fce; font-weight: 600; }
.session-time {
  font-size: 11px;
  color: #94a3b8;
}
</style>
