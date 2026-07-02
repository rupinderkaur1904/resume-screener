import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from "path"
import tailwindcss from "@tailwindcss/vite"

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: '0.0.0.0',
    proxy: {
      '/auth': {
        target: 'http://backend:8000',   // ✅ Docker service name
        changeOrigin: true,
      },
      '/resumes': {
        target: 'http://backend:8000',
        changeOrigin: true,
      },
      '/jobs': {
        target: 'http://backend:8000',
        changeOrigin: true,
      },
      '/matches': {
        target: 'http://backend:8000',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://backend:8000',
        changeOrigin: true,
      },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
})

