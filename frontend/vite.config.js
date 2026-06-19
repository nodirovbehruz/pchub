import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Backend the dev proxy forwards to. Defaults to the local backend; override to point
// the admin at a remote server (e.g. prod) without editing this file:
//   VITE_API_TARGET=http://173.212.221.131 npm run dev
const API_TARGET = process.env.VITE_API_TARGET || 'http://127.0.0.1:8000'
const WS_TARGET = API_TARGET.replace(/^http/, 'ws')

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: API_TARGET,
        changeOrigin: true,
      },
      '/admin': {
        target: API_TARGET,
        changeOrigin: true,
      },
      '/media': {
        target: API_TARGET,
        changeOrigin: true,
      },
      // WebSocket (realtime chat/notifications) → backend ASGI
      '/ws': {
        target: WS_TARGET,
        ws: true,
        changeOrigin: true,
      },
    },
  },
})
