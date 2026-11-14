// PreToolUse safety hook for the Bash and PowerShell tools.
// Based on Matt Pocock's git-guardrails-claude-code (MIT, see GUARD-NOTICE.md), rewritten in Node
// (no jq needed) and changed to the team's rules: task branches may be pushed; pushing or merging
// into main, force pushes, branch deletion and recursive deletes outside scratch folders are blocked.
import { execFileSync } from 'node:child_process';
import { statSync } from 'node:fs';
import { resolve } from 'node:path';
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

// git also expands heads/main to refs/heads/main
const isMainRef = (ref) => ref === MAIN || ref === `refs/heads/${MAIN}` || ref === `heads/${MAIN}`;
// git global options that take the next word as their value
const VALUE_OPTIONS = new Set(['-C', '-c', '--git-dir', '--work-tree', '--namespace', '--exec-path', '--config-env']);

function checkGit(args, state) {
  // skip global options before the subcommand: -C <path>, -c <k=v>, --git-dir <path>, --no-pager and similar
  let i = 0;
  while (i < args.length && args[i].startsWith('-')) {
    // an alias defined on the command line can run any command under another name, so it is never checkable
    if ((args[i] === '-c' || args[i] === '--config-env') && /^alias\./i.test(args[i + 1] ?? '')) {
      return 'defining a git alias inside the command';
    }
    i += VALUE_OPTIONS.has(args[i]) ? 2 : 1;
  }
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
  // ways to write main without merging into it (adversarial review, 2026-11-14)
  if (sub === 'fetch' && plain.some((p) => p.includes(':') && isMainRef(p.split(':').pop().replace(/^\+/, '')))) {
    return 'fetching into main';
  }
  if (sub === 'update-ref' && plain.some(isMainRef)) return 'moving main with update-ref';
  if (sub === 'symbolic-ref' && plain.some(isMainRef)) return 'pointing HEAD at main';
  if (sub === 'branch' && has('-f', '--force', '-m', '-M', '--move', '-c', '-C', '--copy') && plain.some(isMainRef)) {
    return 'moving or overwriting main';
  }
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

// Text that merges a pull request however the command is wrapped: `pr` followed only by options and then `merge`
// (gh pr merge, gh pr -R x merge, pr merge inside quotes), and the merge calls of the GitHub API.
const MERGE_TEXT = /\bpr\s+(?:-{1,2}\S+\s+(?:[^-\s]\S*\s+)?)*merge\b|\/pulls\/[^/\s]+\/merge\b|\/merges\b|mergePullRequest|enablePullRequestAutoMerge/i;
const isPlainMerge = (seg) => seg[0] === 'gh' && seg[1] === 'pr' && seg[2] === 'merge';

// The checks of one command line against the branch it runs on; a reason string when it must be blocked, else null.
function checkCommand(command, { currentBranch = null, shell = 'bash' } = {}) {
  // only the plain command `gh pr merge ...`, alone, reaches the merge gate (mergeRequest); any other text that would
  // merge a pull request (behind a wrapper, a shell, eval, a path or the API) is blocked, whatever runs it
  const segs = segments(tokenize(command));
  if (MERGE_TEXT.test(command) && !(segs.length === 1 && isPlainMerge(segs[0]))) {
    return 'merging a pull request in a form the merge gate cannot check; run gh pr merge <number> --merge alone ' +
      '(if this is only text, such as a commit message, pass it from a file)';
  }
  const state = { branch: currentBranch };
  for (const seg of segs) {
    let words = seg;
    while (words.length && /^[A-Za-z_][A-Za-z0-9_]*=/.test(words[0])) words = words.slice(1);
    if (!words.length) continue;
    const head = words[0].split(/[\\/]/).pop().toLowerCase().replace(/\.exe$/, '');
    let reason = null;
    if ((head === 'bash' || head === 'sh' || head === 'zsh') && words[1] === '-c' && words[2]) {
      reason = checkCommand(words[2], { currentBranch: state.branch, shell: 'bash' });
    } else if ((head === 'powershell' || head === 'pwsh') && /^-c(ommand)?$/i.test(words[1] || '') && words[2]) {
      reason = checkCommand(words.slice(2).join(' '), { currentBranch: state.branch, shell: 'powershell' });
    } else if (head === 'git') {
      reason = checkGit(words.slice(1), state);
    } else if (RM_WORDS.has(head)) {
      reason = checkRm(words.slice(1), head === 'rm' && shell !== 'powershell' ? 'bash' : shell);
    }
    if (reason) return reason;
  }
  return null;
}

// ---- folders (team, 2026-11-14): only stricter than the session-folder rule, with one narrow exception ----
// Words that change the folder, run text as a command or point git elsewhere: any of them cancels the exception.
const FOLDER_WORDS = new Set(['cd', 'pushd', 'popd', 'chdir', 'builtin', 'command', 'exec', 'eval', 'env', 'source',
  '.', 'sh', 'bash', 'zsh', 'set-location', 'sl', 'push-location', 'pop-location', 'iex', 'invoke-expression',
  'start-process', 'powershell', 'pwsh', 'export', 'declare', 'typeset', 'readonly', 'local', 'set', 'alias',
  'function', 'trap', 'source']);
// git options that point it at another repository or run configured commands (aliases with !)
const GIT_REPO_OPTION = /^(?:-C|-c|--git-dir|--work-tree|--config-env)(?:=|$)/;
const UNREADABLE = /[$`*?~!]/;

// A literal absolute folder path (Git Bash /d/x becomes D:/x on Windows), or null.
function literalFolder(raw) {
  if (!raw || UNREADABLE.test(raw) || !/^(?:[A-Za-z]:[\\/]|\/)/.test(raw)) return null;
  return process.platform === 'win32' && /^\/[a-zA-Z]\//.test(raw) ? `${raw[1].toUpperCase()}:${raw.slice(2)}` : raw;
}

// git subcommands that cannot change which branch the checkout is on; fetch, merge and push only without a refspec
// (no ':') and without a target ending in main (team, 2026-11-14, after the adversarial review)
const SAFE_GIT = new Set(['status', 'log', 'diff', 'show', 'add', 'commit', 'rev-parse', 'fetch', 'merge', 'push']);

function safeStep(words) {
  if (words[0].split(/[\\/]/).pop().toLowerCase().replace(/\.exe$/, '') !== 'git') return false;
  let i = 1;
  while (i < words.length && words[i].startsWith('-')) i += VALUE_OPTIONS.has(words[i]) ? 2 : 1;
  const sub = words[i];
  if (!SAFE_GIT.has(sub)) return false;
  const plain = words.slice(i + 1).filter((w) => !w.startsWith('-'));
  if (sub === 'merge') return plain.every((w) => !w.includes(':'));
  if (sub === 'fetch' || sub === 'push') {
    return plain.every((w) => !w.includes(':') && w !== '.' && !(sub === 'push' && /(^|\/)main$/.test(w)));
  }
  return true;
}

// The checkout a bash command certainly runs in, when it names one: `cd <literal path>` as the first step with every
// step joined by && (nothing runs if the cd fails), or a single `git -C <literal path> ...`. The folder must be a git
// checkout on a branch other than main. Anything else returns null and the session folder's branch applies.
function certainFolder(command, shell, branchAt) {
  if (shell !== 'bash' || !branchAt || /[(){}`\n$<>]/.test(command)) return null;
  const tokens = tokenize(command);
  if (tokens.some((t) => SEPARATORS.has(t) && t !== '&&')) return null;
  const segs = segments(tokens);
  if (!segs.length || segs.some((s) => /^[A-Za-z_][A-Za-z0-9_]*=/.test(s[0]))) return null;
  const [first] = segs;
  let folder = null;
  let rest = segs;
  if (first[0] === 'cd' && first.length === 2) {
    folder = literalFolder(first[1]);
    rest = segs.slice(1);
  } else if (segs.length === 1 && first[0] === 'git' && first[1] === '-C') {
    folder = literalFolder(first[2]);
    rest = [['git', ...first.slice(3)]];
  }
  if (!folder || command.includes('\\')) return null;
  for (const s of rest) {
    const head = s[0].split(/[\\/]/).pop().toLowerCase().replace(/\.exe$/, '');
    if (FOLDER_WORDS.has(head) || s.some((w) => GIT_REPO_OPTION.test(w))) return null;
    if (!safeStep(s)) return null;
  }
  const branch = branchAt(folder);
  return typeof branch === 'string' && branch !== '' && branch !== MAIN ? { folder, branch } : null;
}

// New block: a git command whose -C folders (each from the previous one, as git reads them) end on main or in a
// folder whose branch cannot be read is checked as if it ran on main.
function gitFolderReason(command, base, branchAt) {
  if (!branchAt) return null;
  for (const seg of segments(tokenize(command))) {
    let words = seg;
    while (words.length && /^[A-Za-z_][A-Za-z0-9_]*=/.test(words[0])) words = words.slice(1);
    if (!words.length || words[0].split(/[\\/]/).pop().toLowerCase().replace(/\.exe$/, '') !== 'git') continue;
    const args = words.slice(1);
    let folder = base;
    let named = false;
    for (let i = 0; i < args.length && args[i].startsWith('-'); i += VALUE_OPTIONS.has(args[i]) ? 2 : 1) {
      if (args[i] !== '-C' || !args[i + 1]) continue;
      named = true;
      const literal = literalFolder(args[i + 1]);
      folder = literal ?? (folder && !UNREADABLE.test(args[i + 1]) ? resolve(folder, args[i + 1]) : null);
    }
    if (!named) continue;
    const branch = folder ? branchAt(folder) : undefined;
    if (branch !== MAIN && branch !== undefined) continue;
    const reason = checkGit(args, { branch: MAIN });
    if (reason) return `${reason} (git -C names a folder on main or one whose branch cannot be read)`;
  }
  return null;
}

// Returns a reason string when the command must be blocked, or null when it may run. branchAt(folder) gives the branch
// checked out in a folder: a name, null (detached HEAD) or undefined (not a readable git checkout).
export function evaluate(command, { currentBranch = null, shell = 'bash', cwd = null, branchAt = null } = {}) {
  const certain = certainFolder(command, shell, branchAt);
  return checkCommand(command, { currentBranch: certain ? certain.branch : currentBranch, shell }) ??
    gitFolderReason(command, certain ? certain.folder : cwd, branchAt);
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

// The branch of a folder for evaluate: undefined unless the folder is a directory inside a git checkout.
function branchAtFolder(folder) {
  try {
    if (!statSync(folder).isDirectory()) return undefined;
    execFileSync('git', ['rev-parse', '--git-dir'], { cwd: folder, stdio: ['ignore', 'ignore', 'ignore'] });
  } catch {
    return undefined;
  }
  return currentBranchOf(folder);
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
    const reason = evaluate(command, { currentBranch: currentBranchOf(cwd), shell, cwd, branchAt: branchAtFolder }) ??
      mergeGateReason(command, cwd);
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
