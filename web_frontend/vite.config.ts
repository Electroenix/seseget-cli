import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:12450',
        changeOrigin: true,
      },
      '/static': {
        target: 'http://localhost:12450',
        changeOrigin: true,
      },
      '/socket.io': {
        target: 'http://localhost:12450',
        changeOrigin: true,
        ws: true,
      },
    },
  },
})
