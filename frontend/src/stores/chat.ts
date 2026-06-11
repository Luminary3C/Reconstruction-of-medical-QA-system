import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { ChatMessage, Session, BackendType, SSEEvent, VerificationEvent } from '@/types/chat';
import { streamChatPython } from '@/api/chat-python';
import { streamChatJava, getSessions, getChatHistory } from '@/api/chat-java';

function newSession(): Session {
  const id = crypto.randomUUID();
  return {
    id,
    title: 'New Chat',
    messages: [],
    createdAt: new Date().toISOString(),
  };
}

export const useChatStore = defineStore('chat', () => {
  // ── Two independent session pools ──
  const pySessions = ref<Session[]>([newSession()]);
  const pyCurrentId = ref<string>(pySessions.value[0].id);

  const jvSessions = ref<Session[]>([newSession()]);
  const jvCurrentId = ref<string>(jvSessions.value[0].id);
  const jvLoadedIds = ref<Set<string>>(new Set());

  const backend = ref<BackendType>('python');
  const isStreaming = ref(false);
  const javaLoggedIn = ref(false);
  const javaUserId = ref('');

  // ── Active pool proxy ──
  const sessions = computed(() => backend.value === 'java' ? jvSessions.value : pySessions.value);
  const currentSessionId = computed(() => backend.value === 'java' ? jvCurrentId.value : pyCurrentId.value);
  const currentSession = computed(() =>
    sessions.value.find((s) => s.id === currentSessionId.value) ?? sessions.value[0]
  );
  const currentMessages = computed(() => currentSession.value.messages);

  function selectSession(id: string) {
    if (backend.value === 'java') {
      jvCurrentId.value = id;
      if (javaLoggedIn.value && !jvLoadedIds.value.has(id)) {
        loadSessionHistory(id);
      }
    } else {
      pyCurrentId.value = id;
    }
  }

  function createSession() {
    const s = newSession();
    if (backend.value === 'java') {
      jvSessions.value.unshift(s);
      jvCurrentId.value = s.id;
    } else {
      pySessions.value.unshift(s);
      pyCurrentId.value = s.id;
    }
  }

  function setBackend(type: BackendType) {
    backend.value = type;
    if (type === 'java' && javaLoggedIn.value) {
      loadJavaSessions();
    }
  }

  function setJavaLoggedIn(loggedIn: boolean) {
    javaLoggedIn.value = loggedIn;
    if (loggedIn && backend.value === 'java') {
      loadJavaSessions();
    }
    if (!loggedIn) {
      // Reset java pool on logout
      jvSessions.value = [newSession()];
      jvCurrentId.value = jvSessions.value[0].id;
      jvLoadedIds.value.clear();
    }
  }

  function setJavaUserId(id: string) {
    javaUserId.value = id;
  }

  // ── Java: remote session list + lazy history ──

  async function loadJavaSessions() {
    try {
      const remoteSessions = await getSessions();
      const merged: Session[] = remoteSessions.map(rs => ({
        id: rs.sessionId,
        title: rs.title || 'New Chat',
        messages: [],
        createdAt: rs.createdAt,
      }));

      // Preserve local empty sessions not yet persisted
      for (const local of jvSessions.value) {
        if (!merged.some(m => m.id === local.id) && local.messages.length === 0) {
          merged.unshift(local);
        }
      }

      jvSessions.value = merged;
      jvLoadedIds.value.clear();

      // If current selection is a remote session, load its history
      const cur = merged.find(s => s.id === jvCurrentId.value);
      if (cur && !jvLoadedIds.value.has(cur.id)) {
        loadSessionHistory(cur.id);
      }
    } catch {
      // Silently fail — local sessions still work
    }
  }

  async function loadSessionHistory(sessionId: string) {
    try {
      const history = await getChatHistory(sessionId);
      const session = jvSessions.value.find(s => s.id === sessionId);
      if (session) {
        const messages: ChatMessage[] = [];
        for (const msg of history) {
          messages.push({ role: 'user', content: msg.question });
          messages.push({ role: 'assistant', content: msg.answer });
        }
        session.messages = messages;
        jvLoadedIds.value.add(sessionId);
      }
    } catch {
      // Silently fail
    }
  }

  // ── Send message ──

  async function sendMessage(content: string): Promise<void> {
    const pool = backend.value === 'java' ? jvSessions.value : pySessions.value;
    const session = pool.find((s) => s.id === currentSessionId.value);
    if (!session) return;

    const userMsg: ChatMessage = { role: 'user', content };
    session.messages.push(userMsg);

    if (session.messages.filter((m) => m.role === 'user').length === 1) {
      session.title = content.slice(0, 30) + (content.length > 30 ? '...' : '');
    }

    isStreaming.value = true;
    session.messages.push({ role: 'assistant', content: '' });
    const msgIndex = session.messages.length - 1;

    try {
      if (backend.value === 'python') {
        for await (const event of streamChatPython({
          messages: session.messages.slice(0, -1),
          stream: true,
          session_id: session.id,
        })) {
          if (typeof event === 'string') {
            session.messages[msgIndex].content += event;
          } else {
            // Verification event — append disclaimer
            const ve = event as VerificationEvent;
            if (ve.disclaimer) {
              session.messages[msgIndex].content += '\n\n' + ve.disclaimer;
            }
          }
        }
      } else {
        for await (const token of streamChatJava({
          message: content,
          sessionId: session.id,
        })) {
          session.messages[msgIndex].content += token;
        }
      }
    } catch (err) {
      session.messages[msgIndex].content = `Error: ${err instanceof Error ? err.message : 'unknown error'}`;
    } finally {
      isStreaming.value = false;
    }
  }

  return {
    sessions,
    currentSessionId,
    backend,
    isStreaming,
    javaLoggedIn,
    javaUserId,
    currentSession,
    currentMessages,
    selectSession,
    createSession,
    setBackend,
    setJavaLoggedIn,
    setJavaUserId,
    sendMessage,
  };
});