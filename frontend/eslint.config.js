// Frontend lint rules for every contributor (D-123, D-125, D-166: member B's web app). CI: npx eslint .
import js from '@eslint/js';
import { defineConfig } from 'eslint/config';
import reactHooks from 'eslint-plugin-react-hooks';
import globals from 'globals';
import tseslint from 'typescript-eslint';

export default defineConfig(
  { ignores: ['dist', 'coverage', 'playwright-report', 'test-results', 'public/cesium'] },
  js.configs.recommended,
  tseslint.configs.strict,
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: { globals: { ...globals.browser } },
    plugins: { 'react-hooks': reactHooks },
    rules: {
      ...reactHooks.configs.recommended.rules,
      complexity: ['error', 14],
      'no-console': 'error',
      eqeqeq: 'error',
      // the backend is reached only through src/api.ts (UI-UX-SPEC section 11)
      'no-restricted-globals': ['error', { name: 'fetch', message: 'Use src/api.ts for every request.' }],
    },
  },
  { files: ['src/api.ts', 'src/api/client.ts'], rules: { 'no-restricted-globals': 'off' } },
  { files: ['scripts/**/*.mjs', '*.config.{js,ts}', 'e2e/**/*.ts'], languageOptions: { globals: { ...globals.node } } },
  { files: ['scripts/**/*.mjs', 'e2e/**/*.ts'], rules: { 'no-console': 'off' } },
);
