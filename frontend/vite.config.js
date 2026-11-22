import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

// Destino del backend según el modo con el que se arranca Vite:
//   npm run dev         -> backend local
//   npm run dev:remoto  -> backend por Tailscale
const API_LOCAL = 'http://localhost:8000'
const API_REMOTA = 'http://servidor-servicio:8000'

export default defineConfig(({ mode }) => {
  const apiTarget = mode === 'remoto' ? API_REMOTA : API_LOCAL

  console.log(`[vite] proxy /api → ${apiTarget}`)

  return {
    plugins: [
      vue(),
      tailwindcss(),
    ],
    server: {
      proxy: {
        '/api': { target: apiTarget, changeOrigin: true },
      },
    },
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
  }
})
