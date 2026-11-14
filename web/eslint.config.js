import js from '@eslint/js';
import reactHooks from 'eslint-plugin-react-hooks';
import globals from 'globals';
import tseslint from 'typescript-eslint';

export default tseslint.config(
  { ignores: ['dist', 'coverage', 'playwright-report', 'test-results', 'pipeline/**/*.py', 'public/cesium'] },
  js.configs.recommended,
  ...tseslint.configs.strict,
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: { globals: { ...globals.browser } },
    plugins: { 'react-hooks': reactHooks },
    rules: {
      ...reactHooks.configs.recommended.rules,
      eqeqeq: 'error',
      'no-console': 'error',
      complexity: ['error', 14],
    },
  },
  { files: ['pipeline/**/*.mjs', '*.config.{js,ts}', 'e2e/**/*.ts'], languageOptions: { globals: { ...globals.node } } },
  { files: ['pipeline/**/*.mjs', 'e2e/**/*.ts'], rules: { 'no-console': 'off' } },
);
