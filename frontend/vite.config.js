import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import fs from 'fs'
import yaml from 'js-yaml'
import { fileURLToPath } from 'url'
import { dirname, resolve } from 'path'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const config = yaml.load(
  fs.readFileSync(resolve(__dirname, '..', 'config.yml'), 'utf-8')
)

export default defineConfig({
  plugins: [vue()],
  server: {
    port: config.frontend_port,
    proxy: {
      '/api': {
        target: `http://localhost:${config.backend_port}`,
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-markdown': ['marked', 'marked-highlight', 'highlight.js'],
          'vendor-katex': ['katex'],
        },
      },
    },
  },
})
