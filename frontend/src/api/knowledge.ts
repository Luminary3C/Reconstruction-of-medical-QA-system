const AGENT_URL = '/v1';

export interface KnowledgeDoc {
  source_id: number;
  name: string;
  source_type: string;
  doc_count: number;
  created_at: string;
}

export interface UploadResult {
  document_id: number;
}

export async function uploadDocument(title: string, content: string, sourceType: string = 'text'): Promise<UploadResult> {
  const res = await fetch(`${AGENT_URL}/knowledge/upload`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, content, source_type: sourceType }),
  });
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
  const json = await res.json();
  return json.data as UploadResult;
}

export async function uploadFile(title: string, file: File, sourceType: string = 'text'): Promise<UploadResult> {
  const form = new FormData();
  form.append('title', title);
  form.append('file', file);
  form.append('source_type', sourceType);
  const res = await fetch(`${AGENT_URL}/knowledge/upload-file`, {
    method: 'POST',
    body: form,
  });
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
  const json = await res.json();
  return json.data as UploadResult;
}

export async function listDocuments(): Promise<KnowledgeDoc[]> {
  const res = await fetch(`${AGENT_URL}/knowledge/documents`);
  if (!res.ok) throw new Error(`List failed: ${res.status}`);
  const json = await res.json();
  return json.data as KnowledgeDoc[];
}

export async function deleteDocument(docId: number): Promise<void> {
  const res = await fetch(`${AGENT_URL}/knowledge/documents/${docId}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(`Delete failed: ${res.status}`);
}