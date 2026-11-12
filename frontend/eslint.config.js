// Frontend lint rules for every contributor (D-123, D-125). CI: npx eslint .
import js from '@eslint/js';
import { defineConfig } from 'eslint/config';
import tseslint from 'typescript-eslint';

export default defineConfig(
  { ignores: ['dist', 'coverage', 'playwright-report', 'test-results'] },
  js.configs.recommended,
  tseslint.configs.strictTypeChecked,
  { languageOptions: { parserOptions: { projectService: true, tsconfigRootDir: import.meta.dirname } } },
  {
    rules: {
      complexity: ['error', 10],
      'max-depth': ['error', 3],
      'no-console': 'error',
      eqeqeq: 'error',
      // the backend is reached only through src/api.ts (UI-UX-SPEC section 11)
      'no-restricted-globals': ['error', { name: 'fetch', message: 'Use src/api.ts for every request.' }],
    },
  },
  { files: ['src/api.ts'], rules: { 'no-restricted-globals': 'off' } },
  { files: ['**/*.js', '**/*.mjs'], extends: [tseslint.configs.disableTypeChecked] },
);
