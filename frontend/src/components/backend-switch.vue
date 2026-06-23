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
    <label class="backend-label">后端：</label>
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
}
.backend-label {
  font-size: 13px;
  color: #64748b;
}
.backend-select {
  padding: 6px 10px;
  border: 1px solid #d0d7e0;
  border-radius: 6px;
  background: #fff;
  color: #1e293b;
  font-size: 13px;
  outline: none;
}
.backend-indicator {
  font-size: 10px;
}
.backend-indicator.python { color: #2c6fce; }
.backend-indicator.java { color: #e74c3c; }
</style>
