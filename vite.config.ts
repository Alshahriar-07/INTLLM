import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '/assets': path.resolve(__dirname, './assets')
    }
  },
  build: {
    rollupOptions: {
      output: {
        // Vendor frameworks and the markdown/highlighter stack are stable,
        // cacheable dependencies: keep them out of the application chunk so
        // app updates do not invalidate the whole bundle.
        manualChunks: {
          'vendor-react': ['react', 'react-dom'],
          'vendor-markdown': ['react-markdown', 'remark-gfm', 'rehype-highlight', 'highlight.js']
        }
      }
    }
  },
  server: {
    port: 3000,
    host: true
  }
});
