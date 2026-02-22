import service from './index'

export const addVM = (vmInfo) => {
  return service.post('/vm/add', vmInfo)
}

export const getVMList = () => {
  return service.get('/vm/list')
}

export const execSSHCommand = (cmdInfo) => {
  return service.post('/vm/ssh/exec', cmdInfo)
}
