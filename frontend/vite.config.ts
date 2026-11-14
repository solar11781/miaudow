/// <reference types="vitest/config" />
import { cpSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import react from '@vitejs/plugin-react';
import { defineConfig, type Plugin } from 'vite';

// B's canonical data files (frontend/data/canonical) feed the extras; the farmer flow and method page read /api.
const canonical = fileURLToPath(new URL('./data/canonical', import.meta.url));
const api = process.env.MIAUDOW_API ?? 'http://127.0.0.1:8000';
const snapshot = fileURLToPath(new URL('./snapshot', import.meta.url));

// The saved real answers (scripts/build_snapshot.py) go into the output of `npm run build:snapshot` only, never the
// normal build.
function snapshotFiles(): Plugin {
  let outDir = '';
  return {
    name: 'snapshot-files',
    apply: (_, env) => env.command === 'build' && env.mode === 'snapshot',
    configResolved: (config) => {
      outDir = resolve(config.root, config.build.outDir);
    },
    closeBundle: () => cpSync(snapshot, resolve(outDir, 'snapshot'), { recursive: true }),
  };
}

// Relative base so the built app also runs from a sub-folder or a static file host (hash routing, no server rewrites).
export default defineConfig({
  base: './',
  plugins: [react(), snapshotFiles()],
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
