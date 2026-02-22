<template>
  <div class="terminal-container" ref="terminalRef" style="width: 100%; height: 400px;"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { Terminal } from 'xterm'
import { FitAddon } from 'xterm-addon-fit'
import 'xterm/css/xterm.css'
import { execSSHCommand } from '@/api/vm'

const props = defineProps({
  vmId: {
    type: Number,
    required: true
  }
})

const terminalRef = ref(null)
let terminal = null
let fitAddon = null

onMounted(() => {
  // 初始化终端
  terminal = new Terminal({
    fontSize: 14,
    theme: {
      background: '#1e1e1e',
      foreground: '#ffffff'
    },
    cursorBlink: true
  })

  fitAddon = new FitAddon()
  terminal.loadAddon(fitAddon)
  terminal.open(terminalRef.value)
  fitAddon.fit()

  // 监听输入
  terminal.onData(async (data) => {
    if (data === '\r') {
      // 回车执行命令
      const cmdLine = terminal.buffer.active.getLine(terminal.buffer.active.cursorY - 1)
      const cmd = cmdLine ? cmdLine.translateToString().trim() : ''
      if (cmd) {
        terminal.writeln('')
        try {
          const res = await execSSHCommand({
            vm_id: props.vmId,
            command: cmd
          })
          // 输出结果
          terminal.writeln(res.data.stdout || '')
          if (res.data.stderr) {
            terminal.writeln(`\x1B[31m${res.data.stderr}\x1B[0m`)
          }
        } catch (e) {
          terminal.writeln(`\x1B[31m执行失败: ${e.message}\x1B[0m`)
        }
        terminal.writeln('')
      }
    } else {
      // 普通输入回显
      terminal.write(data)
    }
  })

  // 欢迎信息
  terminal.writeln('=== SSH终端已连接 ===')
  terminal.writeln('输入命令并按回车执行（如：ls -l）')
  terminal.writeln('')
})

onUnmounted(() => {
  if (terminal) {
    terminal.dispose()
  }
})
</script>
