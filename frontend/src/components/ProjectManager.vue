<template>
  <div class="project-manager">
    <div class="project-header">
      <h3>项目管理</h3>
      <button class="btn-icon" @click="showCreateModal = true" title="创建项目">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="12" y1="5" x2="12" y2="19"></line>
          <line x1="5" y1="12" x2="19" y2="12"></line>
        </svg>
      </button>
      <button class="btn-icon" @click="showUploadModal = true" title="上传文件夹">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="17,8 12,3 7,8"></polyline>
          <line x1="12" y1="3" x2="12" y2="15"></line>
        </svg>
      </button>
    </div>

    <div class="project-list">
      <div v-if="loading" class="loading">加载中...</div>
      
      <div v-else-if="projects.length === 0" class="empty">
        <p>暂无项目</p>
        <p class="hint">创建项目或上传文件夹开始使用</p>
      </div>

      <div
        v-else
        v-for="project in projects"
        :key="project.id"
        class="project-item"
        :class="{ active: currentProject?.id === project.id }"
        @click="$emit('select', project)"
      >
        <div class="project-info">
          <div class="project-name">{{ project.name }}</div>
          <div class="project-meta">
            <span>{{ project.conversation_count || 0 }} 个对话</span>
          </div>
        </div>
        <button class="btn-icon danger" @click.stop="confirmDelete(project)" title="删除项目">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3,6 5,6 21,6"></polyline>
            <path d="M19,6v14a2,2,0,0,1-2,2H7a2,2,0,0,1-2-2V6m3,0V4a2,2,0,0,1,2-2h4a2,2,0,0,1,2,2v2"></path>
          </svg>
        </button>
      </div>
    </div>

    <!-- 创建项目模态框 -->
    <div v-if="showCreateModal" class="modal-overlay" @click.self="showCreateModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>创建项目</h3>
          <button class="btn-close" @click="showCreateModal = false">&times;</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>项目名称</label>
            <input v-model="newProject.name" type="text" placeholder="输入项目名称" />
          </div>
          <div class="form-group">
            <label>描述（可选）</label>
            <textarea v-model="newProject.description" placeholder="输入项目描述" rows="3"></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" @click="showCreateModal = false">取消</button>
          <button class="btn-primary" @click="createProject" :disabled="!newProject.name.trim() || creating">
            {{ creating ? '创建中...' : '创建' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 上传文件夹模态框 -->
    <div v-if="showUploadModal" class="modal-overlay" @click.self="showUploadModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>上传文件夹</h3>
          <button class="btn-close" @click="showUploadModal = false">&times;</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>项目名称</label>
            <input v-model="uploadData.name" type="text" placeholder="留空则使用文件夹名称" />
          </div>
          <div class="form-group">
            <label>文件夹路径</label>
            <div class="input-with-action">
              <input v-model="uploadData.folderPath" type="text" placeholder="输入文件夹绝对路径或点击右侧按钮选择" />
              <button class="btn-browse" @click="selectFolder" type="button">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
                </svg>
                选择文件夹
              </button>
            </div>
          </div>
          <div class="form-group">
            <label>描述（可选）</label>
            <textarea v-model="uploadData.description" placeholder="输入项目描述" rows="3"></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" @click="showUploadModal = false">取消</button>
          <button class="btn-primary" @click="uploadFolder" :disabled="!uploadData.folderPath.trim() || uploading">
            {{ uploading ? '上传中...' : '上传' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 删除确认模态框 -->
    <div v-if="showDeleteModal" class="modal-overlay" @click.self="showDeleteModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>确认删除</h3>
          <button class="btn-close" @click="showDeleteModal = false">&times;</button>
        </div>
        <div class="modal-body">
          <p>确定要删除项目 <strong>{{ projectToDelete?.name }}</strong> 吗？</p>
          <p class="warning">这将同时删除项目中的所有文件和对话记录，此操作不可恢复。</p>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" @click="showDeleteModal = false">取消</button>
          <button class="btn-danger" @click="deleteProject" :disabled="deleting">
            {{ deleting ? '删除中...' : '删除' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { projectApi } from '../api'

const props = defineProps({
  currentProject: Object,
})

const emit = defineEmits(['select', 'created', 'deleted'])

const projects = ref([])
const loading = ref(false)
const showCreateModal = ref(false)
const showUploadModal = ref(false)
const showDeleteModal = ref(false)
const creating = ref(false)
const uploading = ref(false)
const deleting = ref(false)
const projectToDelete = ref(null)

const newProject = ref({
  name: '',
  description: '',
})

const uploadData = ref({
  name: '',
  folderPath: '',
  description: '',
})

async function selectFolder() {
  try {
    if ('showDirectoryPicker' in window) {
      const dirHandle = await window.showDirectoryPicker()
      // 将文件夹名称自动填入项目名（如未填写）
      if (!uploadData.value.name.trim()) {
        uploadData.value.name = dirHandle.name
      }
      // 提示用户手动确认服务器路径
      if (!uploadData.value.folderPath.trim()) {
        uploadData.value.folderPath = dirHandle.name
      }
    }
  } catch (e) {
    if (e.name !== 'AbortError') {
      console.error('Failed to select folder:', e)
    }
  }
}

// 固定用户ID（实际应用中应从登录状态获取）
const userId = 1

async function loadProjects() {
  loading.value = true
  try {
    const res = await projectApi.list(userId)
    projects.value = res.data.projects || []
  } catch (e) {
    console.error('Failed to load projects:', e)
  } finally {
    loading.value = false
  }
}

async function createProject() {
  if (!newProject.value.name.trim()) return
  
  creating.value = true
  try {
    const res = await projectApi.create({
      user_id: userId,
      name: newProject.value.name.trim(),
      description: newProject.value.description.trim(),
    })
    projects.value.unshift(res.data)
    showCreateModal.value = false
    newProject.value = { name: '', description: '' }
    emit('created', res.data)
  } catch (e) {
    console.error('Failed to create project:', e)
    alert('创建项目失败: ' + e.message)
  } finally {
    creating.value = false
  }
}

async function uploadFolder() {
  if (!uploadData.value.folderPath.trim()) return
  
  uploading.value = true
  try {
    const res = await projectApi.uploadFolder({
      user_id: userId,
      name: uploadData.value.name.trim() || undefined,
      folder_path: uploadData.value.folderPath.trim(),
      description: uploadData.value.description.trim(),
    })
    projects.value.unshift(res.data)
    showUploadModal.value = false
    uploadData.value = { name: '', folderPath: '', description: '' }
    emit('created', res.data)
  } catch (e) {
    console.error('Failed to upload folder:', e)
    alert('上传文件夹失败: ' + e.message)
  } finally {
    uploading.value = false
  }
}

function confirmDelete(project) {
  projectToDelete.value = project
  showDeleteModal.value = true
}

async function deleteProject() {
  if (!projectToDelete.value) return
  
  deleting.value = true
  try {
    await projectApi.delete(projectToDelete.value.id)
    projects.value = projects.value.filter(p => p.id !== projectToDelete.value.id)
    showDeleteModal.value = false
    emit('deleted', projectToDelete.value.id)
    projectToDelete.value = null
  } catch (e) {
    console.error('Failed to delete project:', e)
    alert('删除项目失败: ' + e.message)
  } finally {
    deleting.value = false
  }
}

onMounted(() => {
  loadProjects()
})

defineExpose({
  loadProjects,
})
</script>

<style scoped>
.project-manager {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.project-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-light);
}

.project-header h3 {
  flex: 1;
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.btn-icon {
  padding: 6px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-icon:hover {
  background: var(--bg-hover);
  color: var(--accent-primary);
}

.btn-icon.danger:hover {
  background: var(--danger-bg);
  color: var(--danger-color);
}

.project-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.loading, .empty {
  text-align: center;
  padding: 32px 16px;
  color: var(--text-secondary);
  font-size: 13px;
}

.empty .hint {
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-tertiary);
}

.project-item {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  margin-bottom: 4px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.project-item:hover {
  background: var(--bg-hover);
}

.project-item.active {
  background: var(--accent-primary-light);
}

.project-info {
  flex: 1;
  min-width: 0;
}

.project-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-meta {
  font-size: 12px;
  color: var(--text-tertiary);
}

/* Modal styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--overlay-bg);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: var(--bg-primary);
  border-radius: 12px;
  width: 90%;
  max-width: 480px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-light);
}

.modal-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.btn-close {
  border: none;
  background: transparent;
  font-size: 24px;
  color: var(--text-tertiary);
  cursor: pointer;
  padding: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-close:hover {
  color: var(--text-primary);
}

.modal-body {
  padding: 20px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-group label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.form-group input,
.form-group textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border-input);
  border-radius: 8px;
  background: var(--bg-input);
  color: var(--text-primary);
  font-size: 13px;
  font-family: inherit;
  transition: border-color 0.2s;
}

.input-with-action {
  display: flex;
  gap: 8px;
  align-items: center;
}

.input-with-action input {
  flex: 1;
  min-width: 0;
}

.btn-browse {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border: 1px solid var(--border-input);
  border-radius: 8px;
  background: var(--bg-secondary);
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.btn-browse:hover {
  background: var(--bg-hover);
  color: var(--accent-primary);
  border-color: var(--accent-primary);
}

.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: var(--accent-primary);
}

.form-group textarea {
  resize: vertical;
  min-height: 80px;
}

.modal-footer {
  display: flex;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid var(--border-light);
}

.btn-primary,
.btn-secondary,
.btn-danger {
  flex: 1;
  padding: 10px 16px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary {
  background: var(--accent-primary);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: var(--accent-primary-hover);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.btn-secondary:hover {
  background: var(--bg-hover);
}

.btn-danger {
  background: var(--danger-color);
  color: white;
}

.btn-danger:hover:not(:disabled) {
  opacity: 0.9;
}

.btn-danger:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.warning {
  margin-top: 12px;
  padding: 12px;
  background: var(--danger-bg);
  border-radius: 8px;
  font-size: 13px;
  color: var(--danger-color);
}
</style>
