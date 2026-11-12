// Tests for check-deps.mjs, from UI-UX-SPEC section 3 and D-123 (written before the implementation).
// Run: node --test .github/scripts/check-deps.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { checkPackage } from './check-deps.mjs';

const allow = {
  runtime: ['react', 'react-dom', 'react-router-dom'],
  development: ['vite', 'typescript', 'vitest', 'eslint', 'prettier'],
};

test('allowed packages with exact versions pass', () => {
  const pkg = { dependencies: { react: '19.2.0' }, devDependencies: { vite: '7.1.3', eslint: '10.14.0' } };
  assert.deepEqual(checkPackage(pkg, allow), []);
  assert.deepEqual(checkPackage({}, allow), []);
});

test('a runtime package not on the runtime list fails', () => {
  assert.match(checkPackage({ dependencies: { lodash: '4.17.21' } }, allow).join(), /lodash/);
});

test('a development tool used as a runtime dependency fails (it would ship)', () => {
  assert.match(checkPackage({ dependencies: { eslint: '10.14.0' } }, allow).join(), /eslint/);
});

test('a development package not on any list fails', () => {
  assert.match(checkPackage({ devDependencies: { 'left-pad': '1.3.0' } }, allow).join(), /left-pad/);
});

test('runtime packages may also be listed as development dependencies', () => {
  assert.deepEqual(checkPackage({ devDependencies: { react: '19.2.0' } }, allow), []);
});

test('versions must be exact', () => {
  for (const v of ['^19.2.0', '~19.2.0', '*', 'latest', '>=19', '19.x', '19']) {
    assert.match(checkPackage({ dependencies: { react: v } }, allow).join(), /exact/, v);
  }
});
