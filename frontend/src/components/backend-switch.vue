<script setup lang="ts">
import { useChatStore } from '@/stores/chat';
import type { BackendType } from '@/types/chat';

const store = useChatStore();

const options: { label: string; value: BackendType }[] = [
  { label: 'Python Agent', value: 'python' },
  { label: 'Java Gateway', value: 'java' },
];

function onChange(e: Event) {
  const val = (e.target as HTMLSelectElement).value as BackendType;
  store.setBackend(val);
}
</script>

<template>
  <div class="backend-switch">
    <label class="backend-label">Backend:</label>
    <select class="backend-select" :value="store.backend" @change="onChange">
      <option v-for="o in options" :key="o.value" :value="o.value">{{ o.label }}</option>
    </select>
    <span class="backend-indicator" :class="store.backend">●</span>
  </div>
</template>

<style scoped>
.backend-switch {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: #1a1a2e;
  border-bottom: 1px solid #333;
}
.backend-label {
  font-size: 13px;
  color: #888;
}
.backend-select {
  padding: 4px 8px;
  border: 1px solid #444;
  border-radius: 4px;
  background: #16213e;
  color: #eee;
  font-size: 13px;
  outline: none;
}
.backend-indicator {
  font-size: 10px;
}
.backend-indicator.python {
  color: #4ecdc4;
}
.backend-indicator.java {
  color: #ff6b6b;
}
</style>
