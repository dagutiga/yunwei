import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      // 新增：显式解析Vue相关模块
      'vue': path.resolve(__dirname, 'node_modules/vue'),
      '@vue/shared': path.resolve(__dirname, 'node_modules/@vue/shared')
    },
    // 新增：指定扩展名解析顺序
    extensions: ['.mjs', '.js', '.jsx', '.json', '.vue']
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    minify: 'esbuild',
    // 新增：忽略rollup的外部依赖警告（可选）
    rollupOptions: {
      external: [],
      onwarn(warning, warn) {
        // 忽略"@vue/shared"相关的解析警告
        if (warning.code === 'UNKNOWN_IMPORT' && warning.source === '@vue/shared') {
          return;
        }
        warn(warning);
      }
    }
  }
})
