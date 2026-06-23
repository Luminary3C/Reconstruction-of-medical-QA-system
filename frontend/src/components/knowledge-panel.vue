<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useChatStore } from '@/stores/chat';

const store = useChatStore();

const title = ref('');
const body = ref('');
const sourceType = ref('text');
const uploading = ref(false);
const uploadError = ref('');
const uploadMode = ref<'text' | 'file'>('file');
const selectedFile = ref<File | null>(null);
const fileInputRef = ref<HTMLInputElement | null>(null);

onMounted(() => {
  store.loadKnowledgeDocs();
});

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement;
  if (input.files && input.files.length > 0) {
    selectedFile.value = input.files[0];
    if (!title.value) {
      title.value = input.files[0].name.replace(/\.[^.]+$/, '');
    }
  }
}

function triggerFileInput() {
  fileInputRef.value?.click();
}

async function handleUpload() {
  uploadError.value = '';
  uploading.value = true;
  try {
    if (uploadMode.value === 'file' && selectedFile.value) {
      const t = title.value.trim() || selectedFile.value.name;
      await store.uploadKnowledgeFile(t, selectedFile.value, sourceType.value);
      selectedFile.value = null;
      if (fileInputRef.value) fileInputRef.value.value = '';
    } else {
      const t = title.value.trim();
      const b = body.value.trim();
      if (!t || !b) return;
      await store.uploadKnowledgeDoc(t, b, sourceType.value);
      body.value = '';
    }
    title.value = '';
  } catch (e) {
    uploadError.value = e instanceof Error ? e.message : '上传失败';
  } finally {
    uploading.value = false;
  }
}

async function handleDelete(docId: number) {
  await store.deleteKnowledgeDoc(docId);
}
</script>

<template>
  <div class="knowledge-page">
    <div class="kb-content">
      <!-- Upload Section -->
      <section class="upload-section">
        <h2 class="section-title">上传文档</h2>

        <!-- Mode toggle -->
        <div class="mode-tabs">
          <button
            class="mode-tab"
            :class="{ active: uploadMode === 'file' }"
            @click="uploadMode = 'file'"
            :disabled="!store.isRoot"
          >
            选择文件
          </button>
          <button
            class="mode-tab"
            :class="{ active: uploadMode === 'text' }"
            @click="uploadMode = 'text'"
            :disabled="!store.isRoot"
          >
            粘贴文本
          </button>
        </div>

        <!-- File mode -->
        <template v-if="uploadMode === 'file'">
          <input
            ref="fileInputRef"
            type="file"
            accept=".txt,.pdf,.md,.docx,.doc"
            class="file-input-hidden"
            :disabled="!store.isRoot"
            @change="onFileChange"
          />
          <div class="file-picker" @click="triggerFileInput">
            <template v-if="selectedFile">
              <span class="file-name">{{ selectedFile.name }}</span>
              <span class="file-size">({{ (selectedFile.size / 1024).toFixed(1) }} KB)</span>
            </template>
            <template v-else>
              <span class="file-placeholder">点击选择文件（支持 .txt / .pdf / .md / .docx）</span>
            </template>
          </div>
          <div class="form-grid">
            <div class="form-field">
              <label class="field-label">文档标题</label>
              <input
                v-model="title"
                class="kb-input"
                placeholder="输入文档标题"
                :disabled="!store.isRoot"
              />
            </div>
            <div class="form-field">
              <label class="field-label">来源类型</label>
              <select v-model="sourceType" class="kb-select" :disabled="!store.isRoot">
                <option value="text">纯文本</option>
                <option value="pdf">PDF</option>
                <option value="url">URL</option>
              </select>
            </div>
          </div>
        </template>

        <!-- Text mode -->
        <template v-else>
          <div class="form-grid">
            <div class="form-field">
              <label class="field-label">文档标题</label>
              <input
                v-model="title"
                class="kb-input"
                placeholder="例如：2024 高血压临床指南"
                :disabled="!store.isRoot"
              />
            </div>
            <div class="form-field">
              <label class="field-label">来源类型</label>
              <select v-model="sourceType" class="kb-select" :disabled="!store.isRoot">
                <option value="text">纯文本</option>
                <option value="pdf">PDF</option>
                <option value="url">URL</option>
              </select>
            </div>
          </div>
          <div class="form-field">
            <label class="field-label">文档内容</label>
            <textarea
              v-model="body"
              class="kb-textarea"
              rows="8"
              placeholder="在此粘贴文档内容…"
              :disabled="!store.isRoot"
            ></textarea>
          </div>
        </template>

        <div class="upload-row">
          <button
            class="upload-btn"
            :disabled="!store.isRoot || uploading"
            :title="store.isRoot ? '上传文档' : '仅管理员可操作'"
            @click="handleUpload"
          >
            {{ uploading ? '上传中…' : '上传文档' }}
          </button>
          <span v-if="uploadError" class="upload-error">{{ uploadError }}</span>
          <span v-if="!store.isRoot" class="perm-hint">请以 root 身份登录以管理知识库</span>
        </div>
      </section>

      <!-- Document List Section -->
      <section class="doc-list-section">
        <div class="section-header">
          <h2 class="section-title">文档列表（{{ store.knowledgeDocs.length }}）</h2>
          <button class="refresh-btn" @click="store.loadKnowledgeDocs()" :disabled="store.knowledgeLoading">
            刷新
          </button>
        </div>

        <table class="doc-table" v-if="store.knowledgeDocs.length > 0">
          <thead>
            <tr>
              <th>文档名称</th>
              <th>类型</th>
              <th>分块数</th>
              <th>创建时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="doc in store.knowledgeDocs" :key="doc.source_id">
              <td class="doc-name-cell">{{ doc.name }}</td>
              <td><span class="type-badge">{{ doc.source_type }}</span></td>
              <td>{{ doc.doc_count }}</td>
              <td>{{ new Date(doc.created_at).toLocaleDateString() }}</td>
              <td>
                <button
                  class="delete-btn"
                  :disabled="!store.isRoot"
                  :title="store.isRoot ? '删除文档' : '仅管理员可操作'"
                  @click="handleDelete(doc.source_id)"
                >
                  删除
                </button>
              </td>
            </tr>
          </tbody>
        </table>

        <div v-else-if="!store.knowledgeLoading" class="empty-state">
          <p class="empty-icon">📄</p>
          <p class="empty-text">暂无文档</p>
          <p class="empty-hint">上传医学文档以构建 RAG 检索知识库</p>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.knowledge-page {
  flex: 1;
  background: #f0f4f8;
  overflow-y: auto;
  display: flex;
  justify-content: center;
}
.kb-content {
  width: 100%;
  max-width: 900px;
  padding: 28px 24px;
  display: flex;
  flex-direction: column;
  gap: 28px;
}

section {
  background: #ffffff;
  border: 1px solid #dde4ed;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 16px;
}
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.section-header .section-title { margin-bottom: 0; }

.mode-tabs {
  display: flex;
  gap: 0;
  margin-bottom: 16px;
  border: 1px solid #d0d7e0;
  border-radius: 8px;
  overflow: hidden;
  width: fit-content;
}
.mode-tab {
  padding: 8px 20px;
  border: none;
  background: #ffffff;
  color: #64748b;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}
.mode-tab + .mode-tab { border-left: 1px solid #d0d7e0; }
.mode-tab.active {
  background: #2c6fce;
  color: #ffffff;
}
.mode-tab:disabled {
  color: #cbd5e1;
  cursor: not-allowed;
}

.file-input-hidden { display: none; }
.file-picker {
  border: 2px dashed #d0d7e0;
  border-radius: 8px;
  padding: 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.15s;
  margin-bottom: 12px;
}
.file-picker:hover {
  border-color: #2c6fce;
  background: #f0f6ff;
}
.file-name {
  font-size: 14px;
  font-weight: 500;
  color: #1e293b;
}
.file-size {
  font-size: 12px;
  color: #94a3b8;
  margin-left: 8px;
}
.file-placeholder {
  font-size: 14px;
  color: #94a3b8;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 200px;
  gap: 12px;
  margin-bottom: 12px;
}
.form-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 12px;
}
.field-label {
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.kb-input, .kb-textarea, .kb-select {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d0d7e0;
  border-radius: 8px;
  font-size: 14px;
  font-family: inherit;
  color: #1e293b;
  background: #fff;
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.kb-input:focus, .kb-textarea:focus, .kb-select:focus {
  border-color: #2c6fce;
  box-shadow: 0 0 0 3px rgba(44,111,206,0.1);
}
.kb-input:disabled, .kb-textarea:disabled, .kb-select:disabled {
  background: #f5f7fa;
  color: #94a3b8;
  cursor: not-allowed;
}
.kb-textarea {
  resize: vertical;
  min-height: 120px;
}
.upload-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.upload-btn {
  padding: 10px 24px;
  border: none;
  border-radius: 8px;
  background: #2c6fce;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.15s;
}
.upload-btn:hover:not(:disabled) { background: #1a5ab8; }
.upload-btn:disabled {
  background: #cbd5e1;
  cursor: not-allowed;
}
.upload-error { color: #e74c3c; font-size: 13px; }
.perm-hint { color: #94a3b8; font-size: 12px; }

.refresh-btn {
  padding: 6px 14px;
  border: 1px solid #d0d7e0;
  border-radius: 6px;
  background: #ffffff;
  color: #64748b;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
}
.refresh-btn:hover:not(:disabled) { border-color: #2c6fce; color: #2c6fce; }
.refresh-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.doc-table {
  width: 100%;
  border-collapse: collapse;
}
.doc-table th {
  text-align: left;
  font-size: 11px;
  font-weight: 600;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 8px 12px;
  border-bottom: 2px solid #e8edf2;
}
.doc-table td {
  padding: 12px;
  font-size: 13px;
  color: #1e293b;
  border-bottom: 1px solid #f0f4f8;
}
.doc-table tr:hover td { background: #fafbfc; }
.doc-name-cell {
  font-weight: 500;
  max-width: 280px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.type-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  background: #e8f0fe;
  color: #2c6fce;
  font-size: 11px;
  font-weight: 500;
  text-transform: uppercase;
}
.delete-btn {
  padding: 5px 14px;
  border: 1px solid #fecaca;
  border-radius: 6px;
  background: #fef2f2;
  color: #dc2626;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s;
}
.delete-btn:hover:not(:disabled) { background: #fecaca; }
.delete-btn:disabled {
  background: #f5f7fa;
  border-color: #dde4ed;
  color: #cbd5e1;
  cursor: not-allowed;
}

.empty-state {
  text-align: center;
  padding: 40px 0;
}
.empty-icon { font-size: 36px; margin-bottom: 8px; }
.empty-text { font-size: 15px; color: #64748b; font-weight: 500; }
.empty-hint { font-size: 13px; color: #94a3b8; margin-top: 4px; }
</style>
