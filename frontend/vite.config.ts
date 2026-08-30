import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from "path"
import tailwindcss from "@tailwindcss/vite"

// Proxy target: Docker sets VITE_PROXY_TARGET=http://backend:8000 via env.
// Local dev defaults to http://localhost:9000 (where the backend runs locally).
const apiTarget = process.env.VITE_PROXY_TARGET || 'http://localhost:9000'
const apiRoutes = ['/auth', '/resumes', '/jobs', '/matches', '/health']

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: '0.0.0.0',
    proxy: Object.fromEntries(
      apiRoutes.map((route) => [
        route,
        { target: apiTarget, changeOrigin: true },
      ]),
    ),
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
})

