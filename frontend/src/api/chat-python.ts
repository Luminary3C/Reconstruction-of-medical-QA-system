import type { PythonChatRequest, SSEEvent, VerificationEvent, SourcesEvent } from '@/types/chat';

interface SSEChunk {
  choices: { delta: { content?: string } }[];
}

const AGENT_URL = '/v1';

export async function* streamChatPython(req: PythonChatRequest): AsyncGenerator<SSEEvent, void, void> {
  const res = await fetch(`${AGENT_URL}/chat/completions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });

  if (!res.ok) {
    throw new Error(`Python Agent error: ${res.status}`);
  }

  if (!req.stream) {
    const json = await res.json() as { choices: { message: { content: string } }[] };
    yield json.choices[0].message.content;
    return;
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
      if (!trimmed.startsWith('data: ') || trimmed === 'data: [DONE]') continue;
      const payload = trimmed.slice(6).trimStart();

      try {
        const parsed = JSON.parse(payload);
        if (parsed.type === 'verification') {
          yield parsed as VerificationEvent;
          continue;
        }
        if (parsed.type === 'sources') {
          yield parsed as SourcesEvent;
          continue;
        }
        const chunk = parsed as SSEChunk;
        const content = chunk.choices[0]?.delta?.content;
        if (content) yield content;
      } catch {
        // skip malformed lines
      }
    }
  }
}