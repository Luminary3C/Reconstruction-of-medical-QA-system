import { javaClient } from './client';
import type { JavaChatRequest, JavaChatMessage, LoginRequest, LoginResponse, JavaSessionSummary } from '@/types/chat';
import type { ApiResponse } from '@/types/api';

export async function login(req: LoginRequest): Promise<LoginResponse> {
  const res = await javaClient.post<ApiResponse<LoginResponse>>('/auth/login', req);
  return res.data.data;
}

export async function* streamChatJava(req: JavaChatRequest): AsyncGenerator<string, void, void> {
  const token = localStorage.getItem('jwt-token');
  const res = await fetch('/api/v1/chat/ask', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ message: req.message, sessionId: req.sessionId }),
  });

  if (!res.ok) {
    throw new Error(`Java Gateway error: ${res.status}`);
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error('no response body');

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed.startsWith('data:') || trimmed === 'data:[DONE]') continue;
      const payload = trimmed.slice(5).trimStart();
      yield payload;
    }
  }
}

export async function getSessions(): Promise<JavaSessionSummary[]> {
  const res = await javaClient.get<ApiResponse<JavaSessionSummary[]>>('/chat/sessions');
  return res.data.data;
}

export async function getChatHistory(sessionId: string): Promise<JavaChatMessage[]> {
  const res = await javaClient.get<ApiResponse<JavaChatMessage[]>>(`/chat/history/${sessionId}`);
  return res.data.data;
}
