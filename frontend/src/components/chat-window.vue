<script setup lang="ts">
import { ref, watch, nextTick, computed } from 'vue';
import { useChatStore } from '@/stores/chat';
import { useAutoScroll } from '@/composables/use-sse';
import { renderMarkdown } from '@/composables/use-markdown';

const store = useChatStore();
const inputText = ref('');
const msgsRef = ref<HTMLElement | null>(null);
const { isAtBottom, onScroll, scrollToBottom } = useAutoScroll(msgsRef);

// 流式输出时每收到新 token 都滚动到底部
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

// 渲染消息内容：assistant 用 markdown，user 用纯文本
function renderContent(msg: { role: string; content: string }): string {
  if (msg.role === 'assistant') {
    return renderMarkdown(msg.content);
  }
  return msg.content;
}

// 判断是否是正在流式输出的最后一条 assistant 消息
function isStreamingLast(i: number): boolean {
  const msgs = store.currentMessages;
  return store.isStreaming && i === msgs.length - 1 && msgs[i].role === 'assistant';
}
</script>

<template>
  <main class="chat-window">
    <div class="messages" ref="msgsRef" @scroll="onScroll">
      <div v-if="store.currentMessages.length === 0" class="empty-hint">
        Send a message to start chatting.
      </div>
      <div
        v-for="(m, i) in store.currentMessages"
        :key="i"
        class="message-row"
        :class="m.role"
      >
        <div class="message-bubble" :class="m.role">
          <div class="role-label">{{ m.role === 'user' ? 'You' : 'AI' }}</div>
          <div
            v-if="m.role === 'assistant'"
            class="content md-content"
            v-html="renderContent(m)"
          ></div>
          <div v-else class="content">{{ m.content }}</div>
          <span v-if="isStreamingLast(i)" class="typing-cursor"></span>
        </div>
      </div>
    </div>
    <div class="input-area">
      <textarea
        v-model="inputText"
        class="input-box"
        placeholder="Type a message... (Enter to send, Shift+Enter for newline)"
        rows="2"
        :disabled="store.isStreaming"
        @keydown="onKeydown"
      />
      <button
        class="send-btn"
        :disabled="!inputText.trim() || store.isStreaming"
        @click="handleSend"
      >
        {{ store.isStreaming ? '...' : 'Send' }}
      </button>
    </div>
  </main>
</template>

<style scoped>
.chat-window {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #1a1a2e;
  overflow: hidden;
}
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.empty-hint {
  color: #666;
  text-align: center;
  margin-top: 40px;
  font-size: 14px;
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
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 14px;
  line-height: 1.6;
  position: relative;
}
.message-bubble.user {
  background: #0f3460;
  color: #eee;
}
.message-bubble.assistant {
  background: #1f3050;
  color: #e0e0e0;
}
.role-label {
  font-size: 11px;
  font-weight: 600;
  margin-bottom: 4px;
  opacity: 0.6;
}
.content {
  overflow-wrap: break-word;
}

/* Markdown 渲染样式 */
.md-content {
  overflow-wrap: break-word;
  word-break: break-word;
}

.md-content :deep(h1) { font-size: 1.4em; margin: 0.6em 0 0.3em; border-bottom: 1px solid #444; }
.md-content :deep(h2) { font-size: 1.2em; margin: 0.5em 0 0.2em; }
.md-content :deep(h3) { font-size: 1.1em; margin: 0.4em 0 0.2em; }
.md-content :deep(h4),
.md-content :deep(h5),
.md-content :deep(h6) { font-size: 1em; margin: 0.3em 0; }

.md-content :deep(p) { margin: 0.4em 0; overflow-wrap: break-word; }
.md-content :deep(strong) { color: #fff; font-weight: 700; }
.md-content :deep(em) { color: #a0d0ff; }
.md-content :deep(del) { opacity: 0.5; }

.md-content :deep(ul),
.md-content :deep(ol) { margin: 0.4em 0; padding-left: 1.5em; }

.md-content :deep(ul) { list-style: disc; }
.md-content :deep(ol) { list-style: decimal; }

.md-content :deep(li) { margin: 0.2em 0; overflow-wrap: break-word; }

.md-content :deep(code) {
  background: #0a0a1a;
  color: #4ecdc4;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 0.9em;
  font-family: 'Consolas', 'Monaco', monospace;
  word-break: break-all;
}

.md-content :deep(pre) {
  background: #0a0a1a;
  border: 1px solid #333;
  border-radius: 6px;
  padding: 12px;
  margin: 0.6em 0;
  overflow-x: auto;
  white-space: pre;
}

.md-content :deep(pre code) {
  background: none;
  padding: 0;
  color: #ddd;
  font-size: 0.85em;
  line-height: 1.5;
  white-space: pre;
  word-break: normal;
}

.md-content :deep(a) {
  color: #4ecdc4;
  text-decoration: underline;
}

.md-content :deep(hr) {
  border: none;
  border-top: 1px solid #444;
  margin: 0.8em 0;
}

/* Disclaimer blockquote (verification disclaimer) */
.md-content :deep(blockquote) {
  margin: 0.5em 0;
  padding: 8px 12px;
  background: #2a1a1a;
  border-left: 3px solid #e74c3c;
  color: #f0a0a0;
  font-size: 13px;
  border-radius: 4px;
}

/* 打字机光标 */
.typing-cursor {
  display: inline-block;
  width: 6px;
  height: 16px;
  background: #4ecdc4;
  margin-left: 2px;
  vertical-align: text-bottom;
  animation: blink 0.8s ease-in-out infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.input-area {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid #333;
  background: #16213e;
}
.input-box {
  flex: 1;
  padding: 10px;
  border: 1px solid #444;
  border-radius: 6px;
  background: #1a1a2e;
  color: #eee;
  font-size: 14px;
  resize: none;
  outline: none;
  font-family: inherit;
}
.input-box:focus {
  border-color: #4ecdc4;
}
.send-btn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  background: #0f3460;
  color: #eee;
  font-size: 14px;
  cursor: pointer;
  align-self: flex-end;
}
.send-btn:hover:not(:disabled) {
  background: #1a508b;
}
.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>