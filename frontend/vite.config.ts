/// <reference types="vitest/config" />
import { cpSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import react from '@vitejs/plugin-react';
import license from 'rollup-plugin-license';
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

// Not found by the plugin, so listed by hand: the fonts and the Cesium runtime files ship as files, and
// react-router-dom only re-exports react-router, so the bundle holds none of its own code.
const FILE_PACKAGES = [
  { name: 'cesium', licenseFile: 'LICENSE.md' },
  { name: 'react-router-dom', licenseFile: 'LICENSE.md' },
  ...['@fontsource/be-vietnam-pro', '@fontsource/charm', '@fontsource-variable/alegreya'].map((n) => ({
    name: n,
    licenseFile: 'LICENSE',
  })),
];

// Writes THIRD-PARTY-LICENSES.txt into the build output: the licence text of every package in the JavaScript bundle,
// then the licence of each package in FILE_PACKAGES.
function thirdPartyLicenses(): Plugin[] {
  let outDir = '';
  return [
    {
      name: 'third-party-licenses-dir',
      configResolved: (config) => {
        outDir = resolve(config.root, config.build.outDir);
      },
    },
    // rollup's Plugin type differs slightly from vite's; the hooks used here are the same
    license({
      thirdParty: {
        output: (dependencies) => {
          const packages = dependencies.map(
            (d) => `${d.name} ${d.version} (${d.license})

${d.licenseText ?? '(no licence file in the package)'}`,
          );
          const files = FILE_PACKAGES.map(({ name, licenseFile }) => {
            const dir = resolve('node_modules', name);
            const { version, license: id } = JSON.parse(readFileSync(resolve(dir, 'package.json'), 'utf8')) as {
              version: string;
              license: string;
            };
            return `${name} ${version} (${id})

${readFileSync(resolve(dir, licenseFile), 'utf8')}`;
          });
          mkdirSync(outDir, { recursive: true });
          writeFileSync(
            resolve(outDir, 'THIRD-PARTY-LICENSES.txt'),
            [...packages, ...files].join(`

${'-'.repeat(72)}

`),
          );
        },
      },
    }) as unknown as Plugin,
  ];
}

// Relative base so the built app also runs from a sub-folder or a static file host (hash routing, no server rewrites).
export default defineConfig({
  base: './',
  plugins: [react(), snapshotFiles(), thirdPartyLicenses()],
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
