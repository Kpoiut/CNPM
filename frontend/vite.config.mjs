import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiHost = env.API_HOST || process.env.API_HOST || '127.0.0.1'
  const apiPort = env.API_PORT || process.env.API_PORT || '8000'
  const apiTarget = env.VITE_API_PROXY_TARGET || process.env.VITE_API_PROXY_TARGET || `http://${apiHost}:${apiPort}`

  return {
    plugins: [react(), tailwindcss()],
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
          secure: false,
        },
      },
    },
    build: {
      chunkSizeWarningLimit: 700,
      rolldownOptions: {
        output: {
          chunkFileNames: 'assets/[name]-[hash].js',
          codeSplitting: {
            groups: [
              {
                name: 'three-core',
                test: /node_modules[\\/]three[\\/]/,
                priority: 40,
                maxSize: 260 * 1024,
              },
              {
                name: 'react-three',
                test: /node_modules[\\/](@react-three|@use-gesture|maath|meshline|troika|zustand)[\\/]/,
                priority: 35,
                maxSize: 260 * 1024,
              },
              {
                name: 'charts',
                test: /node_modules[\\/](recharts|d3-|victory-vendor)[\\/]/,
                priority: 30,
                maxSize: 280 * 1024,
              },
              {
                name: 'maps',
                test: /node_modules[\\/](@react-leaflet|leaflet|react-leaflet)[\\/]/,
                priority: 30,
                maxSize: 260 * 1024,
              },
            ],
          },
        },
      },
    },
  }
})
