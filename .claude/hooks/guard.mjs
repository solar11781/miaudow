// PreToolUse safety hook for the Bash and PowerShell tools.
// Based on Matt Pocock's git-guardrails-claude-code (MIT, see GUARD-NOTICE.md), rewritten in Node
// (no jq needed) and changed to the team's rules: task branches may be pushed; pushing or merging
// into main, force pushes, branch deletion and recursive deletes outside scratch folders are blocked.
import { execFileSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';

const MAIN = 'main';
const SCRATCH = new Set(['node_modules', 'dist', 'build', 'coverage', '.playwright-mcp', '__pycache__',
  '.pytest_cache', '.mypy_cache', '.ruff_cache', '.vite']);
const SEPARATORS = new Set(['&&', '||', ';', '|', '&', '\n']);

// Split a command line into words and separators; quoted text stays one word.
function tokenize(cmd) {
  const tokens = [];
  let cur = '';
  let quote = null;
  let started = false;
  const push = () => { if (started) tokens.push(cur); cur = ''; started = false; };
  for (let i = 0; i < cmd.length; i++) {
    const c = cmd[i];
    if (quote) {
      if (c === quote) quote = null;
      else if (c === '\\' && quote === '"' && i + 1 < cmd.length) cur += cmd[++i];
      else cur += c;
      continue;
    }
    if (c === '"' || c === "'") { quote = c; started = true; continue; }
    if (c === '\\' && i + 1 < cmd.length && cmd[i + 1] !== '\n') { cur += cmd[++i]; started = true; continue; }
    if (c === ' ' || c === '\t' || c === '\r') { push(); continue; }
    const two = cmd.slice(i, i + 2);
    if (two === '&&' || two === '||') { push(); tokens.push(two); i++; continue; }
    if (c === ';' || c === '|' || c === '&' || c === '\n') { push(); tokens.push(c); continue; }
    cur += c;
    started = true;
  }
  push();
  return tokens;
}

function segments(tokens) {
  const out = [[]];
  for (const t of tokens) {
    if (SEPARATORS.has(t)) out.push([]);
    else out[out.length - 1].push(t);
  }
  return out.filter((s) => s.length);
}

const isMainRef = (ref) => ref === MAIN || ref === `refs/heads/${MAIN}`;

function checkGit(args, state) {
  // skip global options before the subcommand: -C <path>, -c <k=v>, --no-pager and similar
  let i = 0;
  while (i < args.length && args[i].startsWith('-')) i += (args[i] === '-C' || args[i] === '-c') ? 2 : 1;
  const sub = args[i];
  const rest = args.slice(i + 1);
  const flags = rest.filter((a) => a.startsWith('-'));
  const plain = rest.filter((a) => !a.startsWith('-'));
  const has = (...names) => flags.some((f) => names.includes(f));

  if (sub === 'push') {
    if (has('--force', '-f', '--force-with-lease', '--force-if-includes') ||
        flags.some((f) => f.startsWith('--force-with-lease=')) || plain.some((p) => p.startsWith('+'))) {
      return 'force push';
    }
    if (has('--delete', '-d') || plain.some((p) => p.startsWith(':'))) return 'deleting a remote branch';
    if (has('--all', '--mirror')) return 'pushing all branches, including main';
    const refspecs = plain.slice(1); // plain[0] is the remote
    for (const r of refspecs) {
      const dest = r.includes(':') ? r.split(':').pop() : r;
      if (isMainRef(dest) || (dest === 'HEAD' && state.branch === MAIN)) return 'pushing into main';
    }
    if (refspecs.length === 0 && state.branch === MAIN) return 'pushing into main (current branch is main)';
    return null;
  }
  if (sub === 'merge' && state.branch === MAIN && !has('--abort')) return 'merging into main';
  if (sub === 'rebase' && state.branch === MAIN && !has('--abort')) return 'rewriting main';
  if (sub === 'pull' && state.branch === MAIN && plain.length >= 2 && !plain.slice(1).every(isMainRef)) {
    return 'pulling another branch into main';
  }
  if (sub === 'branch' && has('-d', '-D', '--delete')) return 'deleting a branch';
  if (sub === 'reset' && has('--hard')) return 'git reset --hard';
  if (sub === 'clean' && flags.some((f) => /^-[a-zA-Z]*f/.test(f) || f === '--force')) return 'git clean -f';
  if ((sub === 'checkout' || sub === 'restore') && plain.includes('.')) return `git ${sub} . (discards all changes)`;
  if (sub === 'checkout' || sub === 'switch') {
    const create = has('-b', '-B', '-c', '-C');
    const target = create ? plain[0] : plain[plain.length - 1];
    if (target && !plain.includes('--')) state.branch = target;
  }
  return null;
}

function isScratchPath(raw) {
  const p = raw.replace(/\\/g, '/');
  if (!p || p.includes('$') || p.includes('*') || p.includes('..') || p === '.' || p === '/' || p === '~') return false;
  if (/^\/tmp\//.test(p) || /\/AppData\/Local\/Temp\//i.test(p)) return true;
  return p.split('/').filter(Boolean).some((part) => SCRATCH.has(part));
}

function checkRm(args, shell) {
  const flags = args.filter((a) => a.startsWith('-'));
  const targets = args.filter((a) => !a.startsWith('-'));
  const recursive = shell === 'powershell'
    ? flags.some((f) => /^-r(e(c(u(r(s(e)?)?)?)?)?)?$/i.test(f))
    : flags.some((f) => /^-[a-zA-Z]*[rR]/.test(f) || f === '--recursive');
  if (!recursive) return null;
  if (targets.length === 0) return 'recursive delete without a target';
  const bad = targets.filter((t) => !isScratchPath(t));
  return bad.length ? `recursive delete outside scratch folders (${bad.join(', ')})` : null;
}

const RM_WORDS = new Set(['rm', 'remove-item', 'ri', 'del', 'rd', 'rmdir', 'erase']);
const WRAPPERS = new Set(['env', 'command', 'exec', 'nohup', 'sudo', 'time', 'nice']);

// True when gh would merge a pull request: `gh pr [-R x] merge ...` or a merge through `gh api`.
function isGhMerge(args) {
  if (args[0] === 'api') return args.some((a) => /\/pulls\/[^/\s]+\/merge\b/.test(a) || a.includes('mergePullRequest'));
  if (args[0] !== 'pr') return false;
  let j = 1;
  while (j < args.length && args[j].startsWith('-')) j += (args[j] === '-R' || args[j] === '--repo') ? 2 : 1;
  return args[j] === 'merge';
}

// Returns a reason string when the command must be blocked, or null when it may run.
// nested: the command runs inside bash -c or powershell -Command, where the merge gate cannot see it.
export function evaluate(command, { currentBranch = null, shell = 'bash', nested = false } = {}) {
  const state = { branch: currentBranch };
  for (const seg of segments(tokenize(command))) {
    let words = seg;
    while (words.length && /^[A-Za-z_][A-Za-z0-9_]*=/.test(words[0])) words = words.slice(1);
    // env, command and similar run the next word; skip them with their options and assignments
    while (words.length && WRAPPERS.has(words[0].toLowerCase())) {
      words = words.slice(1);
      while (words.length && (words[0].startsWith('-') || /^[A-Za-z_][A-Za-z0-9_]*=/.test(words[0]))) words = words.slice(1);
    }
    if (!words.length) continue;
    const head = words[0].split(/[\\/]/).pop().toLowerCase().replace(/\.exe$/, '');
    let reason = null;
    // a Windows path loses its backslashes in this bash-style reader (C:\tools\gh.exe reads as C:toolsgh.exe)
    if ((head === 'gh' || /gh$/.test(head)) && isGhMerge(words.slice(1))) {
      // only the plain top-level form reaches the merge gate (mergeRequest); every other way to merge is blocked
      const plain = !nested && words === seg && seg[0] === 'gh' && seg[1] === 'pr' && seg[2] === 'merge';
      if (!plain) reason = 'merging a pull request in a form the merge gate cannot check; use gh pr merge <number> --merge';
    } else if ((head === 'bash' || head === 'sh' || head === 'zsh') && words[1] === '-c' && words[2]) {
      reason = evaluate(words[2], { currentBranch: state.branch, shell: 'bash', nested: true });
    } else if ((head === 'powershell' || head === 'pwsh') && /^-c(ommand)?$/i.test(words[1] || '') && words[2]) {
      reason = evaluate(words.slice(2).join(' '), { currentBranch: state.branch, shell: 'powershell', nested: true });
    } else if (head === 'git') {
      reason = checkGit(words.slice(1), state);
    } else if (RM_WORDS.has(head)) {
      reason = checkRm(words.slice(1), head === 'rm' && shell !== 'powershell' ? 'bash' : shell);
    }
    if (reason) return reason;
  }
  return null;
}

// ---- automatic merge gate (team decision D-124) ----
const GATE_LINE = /^review-gates: spec-review=pass security-review=pass tests=pass\s*$/m;

// When the command merges a pull request, return { pr, problem }; problem is null when the command shape is allowed.
export function mergeRequest(command) {
  const segs = segments(tokenize(command));
  const idx = segs.findIndex((s) => s[0] === 'gh' && s[1] === 'pr' && s[2] === 'merge');
  if (idx === -1) return null;
  const args = segs[idx].slice(3);
  const numbers = args.filter((a) => /^\d+$/.test(a));
  const pr = numbers[0] ?? null;
  // a flag counts by its name: --squash=true is --squash, grouped short flags count one by one (-dm is -d -m),
  // and a short flag with its value attached counts as that flag (-Rother/repo is -R)
  const flagName = (a) => {
    if (a.startsWith('--')) return [a.split('=')[0]];
    if (/^-[a-zA-Z]{2,}$/.test(a)) return [...a.slice(1)].map((c) => `-${c}`);
    return a.startsWith('-') ? [a.slice(0, 2)] : [];
  };
  const flags = args.flatMap(flagName);
  const has = (...f) => flags.some((a) => f.includes(a));
  // the one shape the task skill uses; anything else on the line is refused (an allow-list, not a block-list)
  const extra = args.filter((a) => a !== pr && !['--merge', '--merge=true', '-m'].includes(a));
  let problem = null;
  if (segs.length > 1) problem = 'run the merge command alone, not chained with other commands';
  else if (/[$`#()<>]/.test(command)) problem = 'no shell syntax ($, backtick, #, brackets, redirects) in a merge command';
  else if (!pr) problem = 'name the pull request number';
  else if (numbers.length > 1) problem = 'name exactly one pull request number and nothing else that is a bare number';
  else if (has('-R', '--repo')) problem = 'no -R or --repo (merge only in this repository)';
  else if (has('--admin')) problem = 'no --admin (it bypasses checks)';
  else if (has('--delete-branch', '-d')) problem = 'no --delete-branch (branches are kept)';
  else if (has('--auto')) problem = 'no --auto (merge only after the gate passes now)';
  // normal merges only (team decision D-152, 2026-11-14): main keeps every branch commit; squash and rebase rewrite them
  else if (!has('--merge', '-m') || has('--squash', '-s', '--rebase', '-r')) problem = 'use --merge (or -m) only';
  else if (extra.length > 0) problem = `only gh pr merge <number> --merge is allowed, not: ${extra.join(' ')}`;
  return { pr, problem };
}

// Returns a reason string when the pull request may not be merged yet, or null when every gate passes.
export function checkMergeGate(pr, upToDate) {
  if (pr.state !== 'OPEN') return 'the pull request is not open';
  if (pr.isDraft) return 'the pull request is a draft';
  if (pr.baseRefName !== MAIN) return 'the pull request does not target main';
  if ((pr.files ?? []).some((f) => f.path === '.autopilot/queue.md')) {
    return 'it changes the shared task queue, which a person reviews and merges';
  }
  const checks = pr.statusCheckRollup ?? [];
  if (checks.length === 0) return 'no CI checks reported yet';
  for (const c of checks) {
    const ok = c.__typename === 'StatusContext'
      ? c.state === 'SUCCESS'
      : c.status === 'COMPLETED' && ['SUCCESS', 'SKIPPED', 'NEUTRAL'].includes(c.conclusion);
    if (!ok) return `CI check not passed: ${c.name ?? c.context}`;
  }
  if (!upToDate) return 'the branch does not contain the latest main (update it and let CI run again)';
  const lastCommit = Math.max(...(pr.commits ?? []).map((c) => Date.parse(c.committedDate)));
  const gate = (pr.comments ?? []).some((c) => GATE_LINE.test(c.body) && Date.parse(c.createdAt) > lastCommit);
  if (!gate) return 'no gate record posted after the last commit ("review-gates: spec-review=pass security-review=pass tests=pass")';
  return null;
}

function run(cmd, args, cwd) {
  return execFileSync(cmd, args, { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] });
}

function mergeGateReason(command, cwd) {
  const req = mergeRequest(command);
  if (!req) return null;
  if (req.problem) return `merge refused: ${req.problem}`;
  const pr = JSON.parse(run('gh', ['pr', 'view', req.pr, '--json',
    'state,isDraft,baseRefName,headRefName,statusCheckRollup,commits,comments,files'], cwd));
  run('git', ['fetch', 'origin', MAIN, pr.headRefName, '--quiet'], cwd);
  let upToDate = true;
  try { run('git', ['merge-base', '--is-ancestor', `origin/${MAIN}`, `origin/${pr.headRefName}`], cwd); } catch { upToDate = false; }
  const reason = checkMergeGate(pr, upToDate);
  return reason ? `merge refused: ${reason}` : null;
}

function currentBranchOf(cwd) {
  try {
    return execFileSync('git', ['symbolic-ref', '--short', 'HEAD'], { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
  } catch {
    return null;
  }
}

async function main() {
  let input = '';
  for await (const chunk of process.stdin) input += chunk;
  try {
    const data = JSON.parse(input || '{}');
    const command = data?.tool_input?.command;
    if (typeof command !== 'string') process.exit(0);
    const shell = data.tool_name === 'PowerShell' ? 'powershell' : 'bash';
    const cwd = data.cwd || process.cwd();
    const reason = evaluate(command, { currentBranch: currentBranchOf(cwd), shell }) ?? mergeGateReason(command, cwd);
    if (reason) {
      process.stderr.write(`BLOCKED by the project safety hook: ${reason}. ` +
        'Do not retry or work around it. If it is really needed, stop and ask the team; they run it themselves.\n');
      process.exit(2);
    }
    process.exit(0);
  } catch (err) {
    process.stderr.write(`BLOCKED: the project safety hook could not check this command (${err.message}). Ask the team.\n`);
    process.exit(2);
  }
}

if (import.meta.url === pathToFileURL(process.argv[1] || '').href) main();
