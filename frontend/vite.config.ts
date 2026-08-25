import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'
import { clientLogPlugin } from './server/clientLogPlugin.js'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss(), clientLogPlugin()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
})
