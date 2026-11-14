/// <reference types="vitest/config" />
import { fileURLToPath } from 'node:url';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// B's canonical data files (frontend/data/canonical) feed the extras; the farmer flow and method page read /api.
const canonical = fileURLToPath(new URL('./data/canonical', import.meta.url));
const api = process.env.MIAUDOW_API ?? 'http://127.0.0.1:8000';

// Relative base so the built app also runs from a sub-folder or a static file host (hash routing, no server rewrites).
export default defineConfig({
  base: './',
  plugins: [react()],
  resolve: { alias: { '@data': canonical } },
  server: { proxy: { '/api': api } },
  preview: { proxy: { '/api': api } },
  build: {
    target: 'es2022',
    cssCodeSplit: true,
    rollupOptions: {
      output: {
        manualChunks: (id) => (id.includes('node_modules/react') ? 'react' : undefined),
      },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/tests/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
    css: false,
  },
});
