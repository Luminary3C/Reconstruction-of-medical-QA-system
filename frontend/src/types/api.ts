export interface ApiResponse<T> {
  code: number;
  msg: string;
  data: T;
  traceId: string;
}

export interface SSEChunk {
  id: string;
  object: string;
  created: number;
  model: string;
  choices: SSEChoice[];
}

export interface SSEChoice {
  index: number;
  delta: { content?: string };
  finish_reason: string | null;
}
