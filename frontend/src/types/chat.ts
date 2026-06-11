export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface Session {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: string;
}

export type BackendType = 'python' | 'java';

export interface PythonChatRequest {
  messages: ChatMessage[];
  stream: boolean;
  user_id?: string;
  session_id?: string;
  short_term_context?: string[];
}

export interface JavaChatRequest {
  message: string;
  sessionId?: string;
}

export interface JavaChatMessage {
  id: number;
  userId: string;
  sessionId: string;
  question: string;
  answer: string;
  createdAt: string;
}

export interface VerificationEvent {
  type: 'verification';
  disclaimer: string;
  confidence: 'high' | 'medium' | 'low';
}

export type SSEEvent = string | VerificationEvent;
  sessionId: string;
  title: string;
  createdAt: string;
  messageCount: number;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  token: string;
  userId: string;
  username: string;
}
