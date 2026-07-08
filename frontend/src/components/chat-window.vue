<script setup lang="ts">
import { ref, watch, nextTick } from 'vue';
import { useChatStore } from '@/stores/chat';
import { useAutoScroll } from '@/composables/use-sse';
import { renderMarkdown } from '@/composables/use-markdown';

const store = useChatStore();
const inputText = ref('');
const msgsRef = ref<HTMLElement | null>(null);
const expandedSources = ref<Set<number>>(new Set());
const { isAtBottom, onScroll, scrollToBottom } = useAutoScroll(msgsRef);

watch(
  () => store.currentMessages.map(m => m.content.length),
  () => nextTick(() => { if (isAtBottom.value || store.isStreaming) scrollToBottom(); })
);

watch(
  () => store.currentSessionId,
  () => nextTick(() => scrollToBottom())
);

async function handleSend() {
  const text = inputText.value.trim();
  if (!text || store.isStreaming) return;
  inputText.value = '';
  await store.sendMessage(text);
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    handleSend();
  }
}

function renderContent(msg: { role: string; content: string }): string {
  if (msg.role === 'assistant') {
    return renderMarkdown(msg.content);
  }
  return msg.content;
}

function isStreamingLast(i: number): boolean {
  const msgs = store.currentMessages;
  return store.isStreaming && i === msgs.length - 1 && msgs[i].role === 'assistant';
}

function toggleSource(msgIndex: number) {
  if (expandedSources.value.has(msgIndex)) {
    expandedSources.value.delete(msgIndex);
  } else {
    expandedSources.value.add(msgIndex);
  }
}

function truncate(text: string, maxLen: number = 120): string {
  if (text.length <= maxLen) return text;
  return text.slice(0, maxLen) + '...';
}
</script>

<template>
  <main class="chat-window">
    <div class="messages" ref="msgsRef" @scroll="onScroll">
      <div v-if="store.currentMessages.length === 0" class="empty-hint">
        发送消息开始对话
      </div>
      <div
        v-for="(m, i) in store.currentMessages"
        :key="i"
        class="message-row"
        :class="m.role"
      >
        <div class="message-bubble" :class="m.role">
          <div class="role-label">{{ m.role === 'user' ? '你' : 'AI' }}</div>
          <div
            v-if="m.role === 'assistant'"
            class="content md-content"
            v-html="renderContent(m)"
          ></div>
          <div v-else class="content">{{ m.content }}</div>
          <!-- Knowledge sources citation -->
          <div v-if="m.sources && m.sources.length > 0" class="knowledge-sources">
            <button class="sources-toggle" @click="toggleSource(i)">
              <span class="sources-toggle-icon">{{ expandedSources.has(i) ? '▼' : '▶' }}</span>
              参考知识库（{{ m.sources.length }} 条切片）
            </button>
            <div v-if="expandedSources.has(i)" class="sources-list">
              <div v-for="(src, idx) in m.sources" :key="idx" class="source-item">
                <div class="source-meta">
                  <span class="source-doc-title">{{ src.title }}</span>
                  <span class="source-chunk-index">#{{ src.chunk_index }}</span>
                  <span class="source-score-badge">相关度 {{ (src.similarity * 100).toFixed(0) }}%</span>
                </div>
                <div class="source-content">{{ src.content }}</div>
              </div>
            </div>
          </div>
          <span v-if="isStreamingLast(i)" class="typing-cursor"></span>
        </div>
      </div>
    </div>
    <div class="input-area">
      <textarea
        v-model="inputText"
        class="input-box"
        placeholder="输入医学问题…（Enter 发送，Shift+Enter 换行）"
        rows="2"
        :disabled="store.isStreaming"
        @keydown="onKeydown"
      />
      <button
        class="send-btn"
        :disabled="!inputText.trim() || store.isStreaming"
        @click="handleSend"
      >
        {{ store.isStreaming ? '...' : '发送' }}
      </button>
    </div>
  </main>
</template>

<style scoped>
.chat-window {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #f0f4f8;
  overflow: hidden;
}
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.empty-hint {
  color: #94a3b8;
  text-align: center;
  margin-top: 60px;
  font-size: 15px;
}
.message-row {
  display: flex;
}
.message-row.user {
  justify-content: flex-end;
}
.message-row.assistant {
  justify-content: flex-start;
}
.message-bubble {
  max-width: 80%;
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.65;
  position: relative;
}
.message-bubble.user {
  background: #2c6fce;
  color: #fff;
  border-bottom-right-radius: 4px;
}
.message-bubble.assistant {
  background: #ffffff;
  color: #1e293b;
  border: 1px solid #e8edf2;
  border-bottom-left-radius: 4px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.role-label {
  font-size: 11px;
  font-weight: 600;
  margin-bottom: 4px;
  opacity: 0.5;
}
.message-bubble.user .role-label {
  opacity: 0.7;
}
.content {
  overflow-wrap: break-word;
}

.md-content {
  overflow-wrap: break-word;
  word-break: break-word;
}

.md-content :deep(h1) { font-size: 1.3em; margin: 0.6em 0 0.3em; border-bottom: 1px solid #e8edf2; color: #1e293b; }
.md-content :deep(h2) { font-size: 1.15em; margin: 0.5em 0 0.2em; color: #1e293b; }
.md-content :deep(h3) { font-size: 1.05em; margin: 0.4em 0 0.2em; color: #1e293b; }
.md-content :deep(h4), .md-content :deep(h5), .md-content :deep(h6) { font-size: 1em; margin: 0.3em 0; }

.md-content :deep(p) { margin: 0.4em 0; overflow-wrap: break-word; }
.md-content :deep(strong) { color: #0f172a; font-weight: 700; }
.md-content :deep(em) { color: #2c6fce; }
.md-content :deep(del) { opacity: 0.5; }

.md-content :deep(ul), .md-content :deep(ol) { margin: 0.4em 0; padding-left: 1.5em; }
.md-content :deep(ul) { list-style: disc; }
.md-content :deep(ol) { list-style: decimal; }
.md-content :deep(li) { margin: 0.2em 0; overflow-wrap: break-word; }

.md-content :deep(code) {
  background: #f1f5f9;
  color: #e74c3c;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 0.9em;
  font-family: 'Consolas', 'Monaco', 'Fira Code', monospace;
  word-break: break-all;
}

.md-content :deep(pre) {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 14px;
  margin: 0.6em 0;
  overflow-x: auto;
  white-space: pre;
}

.md-content :deep(pre code) {
  background: none;
  padding: 0;
  color: #1e293b;
  font-size: 0.85em;
  line-height: 1.5;
  white-space: pre;
  word-break: normal;
}

.md-content :deep(a) {
  color: #2c6fce;
  text-decoration: underline;
}

.md-content :deep(hr) {
  border: none;
  border-top: 1px solid #dde4ed;
  margin: 0.8em 0;
}

.md-content :deep(blockquote) {
  margin: 0.5em 0;
  padding: 10px 14px;
  background: #fef2f2;
  border-left: 3px solid #e74c3c;
  color: #991b1b;
  font-size: 13px;
  border-radius: 4px;
}

.typing-cursor {
  display: inline-block;
  width: 6px;
  height: 16px;
  background: #2c6fce;
  margin-left: 2px;
  vertical-align: text-bottom;
  animation: blink 0.8s ease-in-out infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.knowledge-sources {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #e8edf2;
}

.sources-toggle {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: none;
  background: none;
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  padding: 4px 0;
  letter-spacing: 0.3px;
}
.sources-toggle:hover {
  color: #2c6fce;
}

.sources-toggle-icon {
  font-size: 10px;
}

.sources-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 8px;
}

.source-item {
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  padding: 10px 12px;
}

.source-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.source-doc-title {
  font-size: 12px;
  font-weight: 600;
  color: #1e293b;
  max-width: 60%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.source-chunk-index {
  font-size: 11px;
  color: #94a3b8;
  background: #f1f5f9;
  padding: 1px 6px;
  border-radius: 4px;
}

.source-score-badge {
  font-size: 11px;
  color: #2c6fce;
  background: #eef4ff;
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 500;
}

.source-content {
  font-size: 12px;
  line-height: 1.6;
  color: #475569;
  max-height: 120px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

.input-area {
  display: flex;
  gap: 10px;
  padding: 14px 20px;
  border-top: 1px solid #dde4ed;
  background: #ffffff;
}
.input-box {
  flex: 1;
  padding: 12px;
  border: 1px solid #d0d7e0;
  border-radius: 8px;
  background: #ffffff;
  color: #1e293b;
  font-size: 14px;
  resize: none;
  outline: none;
  font-family: inherit;
  transition: border-color 0.15s;
}
.input-box:focus {
  border-color: #2c6fce;
  box-shadow: 0 0 0 3px rgba(44,111,206,0.1);
}
.send-btn {
  padding: 10px 24px;
  border: none;
  border-radius: 8px;
  background: #2c6fce;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  align-self: flex-end;
  transition: background 0.15s;
}
.send-btn:hover:not(:disabled) { background: #1a5ab8; }
.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
