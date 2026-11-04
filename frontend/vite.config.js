import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  // Browser requests stay on /api. Vite forwards them to local FastAPI,
  // so no global CORS permissions or frontend credentials are needed.
  const proxy = {
    '/api': { target: env.QBRIDGE_API_TARGET || 'http://127.0.0.1:8000', changeOrigin: true },
  };
  return {
    plugins: [react(), tailwindcss()],
    server: { port: 5173, strictPort: true, proxy },
    preview: { port: 4173, strictPort: true, proxy },
    // Keep the chart library in its own cacheable production bundle.
    build: { rollupOptions: { output: { manualChunks: { charts: ['recharts'] } } } },
    test: { environment: 'jsdom' },
  };
});
