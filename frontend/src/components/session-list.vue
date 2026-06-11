<script setup lang="ts">
import { useChatStore } from '@/stores/chat';

const store = useChatStore();
</script>

<template>
  <aside class="session-list">
    <button class="new-chat-btn" @click="store.createSession()">+ New Chat</button>
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
  width: 220px;
  background: #16213e;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #333;
  overflow: hidden;
}
.new-chat-btn {
  margin: 12px;
  padding: 10px;
  border: none;
  border-radius: 6px;
  background: #0f3460;
  color: #eee;
  font-size: 14px;
  cursor: pointer;
}
.new-chat-btn:hover {
  background: #1a508b;
}
.sessions {
  list-style: none;
  margin: 0;
  padding: 0;
  overflow-y: auto;
  flex: 1;
}
.session-item {
  padding: 10px 14px;
  cursor: pointer;
  border-bottom: 1px solid #1f3050;
  color: #ccc;
  font-size: 13px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.session-item:hover {
  background: #1f3050;
}
.session-item.active {
  background: #0f3460;
  color: #fff;
}
.session-title {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.session-time {
  font-size: 11px;
  color: #666;
}
</style>
