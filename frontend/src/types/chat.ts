export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  sources?: KnowledgeSource[];
}

export interface KnowledgeSource {
  title: string;
  chunk_index: number;
  content: string;
  score: number;
  similarity: number;
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

export interface SourcesEvent {
  type: 'sources';
  sources: KnowledgeSource[];
}

export type SSEEvent = string | VerificationEvent | SourcesEvent;

export interface JavaSessionSummary {
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
