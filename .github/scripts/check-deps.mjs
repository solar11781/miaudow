// Checks package.json against the dependency allow-list (UI-UX-SPEC section 3, D-123).
// Usage: node .github/scripts/check-deps.mjs <path/to/package.json> [allowlist.json]
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const EXACT = /^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$/;

// Returns a list of problems; an empty list means the file follows the allow-list.
export function checkPackage(pkg, allow) {
  const problems = [];
  const runtime = new Set(allow.runtime);
  const any = new Set([...allow.runtime, ...allow.development]);
  for (const [section, list] of [['dependencies', runtime], ['devDependencies', any]]) {
    for (const [name, version] of Object.entries(pkg[section] ?? {})) {
      if (!list.has(name)) {
        problems.push(section === 'dependencies' && any.has(name)
          ? `${name}: development-only tool listed in dependencies (it would ship)`
          : `${name}: not on the allow-list for ${section} (needs team approval)`);
      }
      if (!EXACT.test(String(version))) problems.push(`${name}: version "${version}" is not exact`);
    }
  }
  return problems;
}

if (import.meta.url === pathToFileURL(process.argv[1] || '').href) {
  const pkgPath = process.argv[2] || 'frontend/package.json';
  const allowPath = process.argv[3] || join(dirname(fileURLToPath(import.meta.url)), 'dependency-allowlist.json');
  const problems = checkPackage(JSON.parse(readFileSync(pkgPath, 'utf8')), JSON.parse(readFileSync(allowPath, 'utf8')));
  for (const p of problems) console.error(`dependency allow-list: ${p}`);
  process.exit(problems.length ? 1 : 0);
}
