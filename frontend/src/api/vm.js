import service from './index'

export const getProjects = () => service.get('/projects')
export const createProject = (payload) => service.post('/projects', payload)
export const upsertProjectMember = (payload) => service.post('/projects/member/upsert', payload)

export const addVM = (vmInfo) => service.post('/vm/add', vmInfo)
export const getVMList = (params) => service.get('/vm/list', { params })
export const execSSHCommand = (cmdInfo) => service.post('/vm/ssh/exec', cmdInfo)

export const offlineCheck = (vmId) => service.post('/vm/offline/check', { vm_id: vmId })
export const applyOffline = (payload) => service.post('/vm/offline/apply', payload)
export const applyDelete = (payload) => service.post('/vm/delete/apply', payload)

export const getMyTasks = () => service.get('/tasks/my')
export const getPendingTasks = () => service.get('/tasks/pending')
export const approveTask = (taskId, payload) => service.post(`/tasks/${taskId}/approve`, payload)

export const exportVMs = (params) => service.get('/vm/export', { params, responseType: 'blob' })
