// Tests for guard.mjs, written from the team's rules (2026-11-13), before the implementation.
// Run: node --test .claude/hooks/
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { evaluate } from './guard.mjs';

const blocked = (cmd, opts = {}) =>
  assert.ok(evaluate(cmd, { currentBranch: 'feat/x', ...opts }), `expected BLOCK: ${cmd}`);
const allowed = (cmd, opts = {}) =>
  assert.equal(evaluate(cmd, { currentBranch: 'feat/x', ...opts }), null, `expected ALLOW: ${cmd}`);

test('rule 1: never push into main', () => {
  blocked('git push origin main');
  blocked('git push -u origin main');
  blocked('git push origin HEAD:main');
  blocked('git push origin feat/x:main');
  blocked('git push origin refs/heads/main');
  blocked('git push --all');
  blocked('git push --mirror origin');
  blocked('git push', { currentBranch: 'main' });
  blocked('git push origin', { currentBranch: 'main' });
  blocked('git push -u origin HEAD', { currentBranch: 'main' });
  blocked('git -C ../repo push origin main');
  blocked('git add . && git commit -m "x" && git push origin main');
  blocked('bash -c "git push origin main"');
});

test('rule 2: task branches may be pushed', () => {
  allowed('git push -u origin feat/plan-cards');
  allowed('git push');
  allowed('git push origin HEAD');
  allowed('git push origin fix/month-bar');
});

test('rule 3: never merge into main', () => {
  blocked('git merge feat/x', { currentBranch: 'main' });
  blocked('git checkout main && git merge feat/x');
  blocked('git switch main; git merge --no-ff feat/x');
  // gh pr merge is handled by the merge gate (D-124), tested below
  blocked('git pull origin feat/x', { currentBranch: 'main' });
  blocked('git rebase feat/x', { currentBranch: 'main' });
  // keeping main up to date from the remote, and updating a task branch from main, are fine
  allowed('git pull', { currentBranch: 'main' });
  allowed('git pull --ff-only origin main', { currentBranch: 'main' });
  allowed('git merge main');
  allowed('git rebase origin/main');
  allowed('git checkout main && git pull && git checkout -b feat/new');
});

test('rule 4: no force pushes on any branch', () => {
  blocked('git push --force origin feat/x');
  blocked('git push -f');
  blocked('git push --force-with-lease');
  blocked('git push --force-if-includes origin feat/x');
  blocked('git push origin +feat/x');
});

test('rule 5: no branch deletion', () => {
  blocked('git branch -d feat/x');
  blocked('git branch -D feat/x');
  blocked('git branch --delete feat/x');
  blocked('git push origin --delete feat/x');
  blocked('git push -d origin feat/x');
  blocked('git push origin :feat/x');
  allowed('git branch');
  allowed('git branch -a');
  allowed('git checkout -b feat/y');
});

test('rule 6: the original guardrail list (Matt Pocock)', () => {
  blocked('git reset --hard');
  blocked('git reset --hard origin/main');
  blocked('git clean -fd');
  blocked('git clean -f');
  blocked('git checkout .');
  blocked('git checkout -- .');
  blocked('git restore .');
  allowed('git reset HEAD~1 --soft');
  allowed('git restore --staged src/a.ts');
  allowed('git checkout src/a.ts');
});

test('rule 7: no recursive delete outside scratch folders', () => {
  blocked('rm -rf src');
  blocked('rm -rf /');
  blocked('rm -rf .');
  blocked('rm -r docs');
  blocked('rm -fr data');
  blocked('rm --recursive --force tests');
  blocked('rm -rf node_modules/../src');
  blocked('rm -rf $HOME');
  blocked('rm -rf *');
  blocked('Remove-Item -Recurse -Force src', { shell: 'powershell' });
  blocked('rm -Recurse docs', { shell: 'powershell' });
  allowed('rm -rf node_modules');
  allowed('rm -rf frontend/dist');
  allowed('rm -rf .playwright-mcp');
  allowed('rm -rf __pycache__ .pytest_cache');
  allowed('rm -rf /tmp/build-123');
  allowed('rm -rf C:/Users/x/AppData/Local/Temp/claude/abc');
  allowed('Remove-Item -Recurse -Force node_modules', { shell: 'powershell' });
  allowed('rm notes.txt');
  allowed('rm -f a.log');
});

test('rule 8: ordinary commands and quoted text are not blocked', () => {
  allowed('git status');
  allowed('git commit -m "docs: never git push origin main or rm -rf /"');
  allowed('npm test');
  allowed('pytest -q');
  allowed('echo "git push --force"');
  allowed('git log --oneline -5');
});

// ---- auto-merge gate (team decisions D-124, 2026-11-13, and D-152, 2026-11-14: normal merges only) ----
import { mergeRequest, checkMergeGate } from './guard.mjs';

test('merge command shape: normal merge, explicit number, no bypass flags', () => {
  assert.deepEqual(mergeRequest('gh pr merge 12 --merge'), { pr: '12', problem: null });
  assert.deepEqual(mergeRequest('gh pr merge 12 -m'), { pr: '12', problem: null });
  assert.equal(mergeRequest('git status'), null);
  assert.match(mergeRequest('gh pr merge --merge').problem, /number/);
  assert.match(mergeRequest('gh pr merge 12').problem, /--merge/);
  assert.match(mergeRequest('gh pr merge 12 --merge --admin').problem, /admin/);
  assert.match(mergeRequest('gh pr merge 12 --merge --delete-branch').problem, /delete/);
  assert.match(mergeRequest('gh pr merge 12 --merge -d').problem, /delete/);
  assert.match(mergeRequest('gh pr merge 12 --merge --auto').problem, /auto/);
  assert.match(mergeRequest('gh pr merge 12 --merge && git push origin main').problem, /alone/);
});

test('squash and rebase merges are refused', () => {
  for (const flag of ['--squash', '-s', '--rebase', '-r']) {
    assert.match(mergeRequest(`gh pr merge 12 ${flag}`).problem, /--merge/, flag);
    assert.match(mergeRequest(`gh pr merge 12 --merge ${flag}`).problem, /--merge/, flag);
  }
});

test('flags written as --flag=value are checked like the plain flag', () => {
  assert.match(mergeRequest('gh pr merge 12 --merge --squash=true').problem, /--merge/);
  assert.match(mergeRequest('gh pr merge 12 --merge --rebase=true').problem, /--merge/);
  assert.match(mergeRequest('gh pr merge 12 --merge --admin=true').problem, /admin/);
  assert.match(mergeRequest('gh pr merge 12 --merge --auto=true').problem, /auto/);
  assert.match(mergeRequest('gh pr merge 12 --merge --delete-branch=true').problem, /delete/);
  assert.deepEqual(mergeRequest('gh pr merge 12 --merge=true'), { pr: '12', problem: null });
});

test('grouped short flags, a second number and another repository are refused', () => {
  assert.match(mergeRequest('gh pr merge 12 --merge -dm').problem, /delete/);
  assert.match(mergeRequest('gh pr merge 12 -md').problem, /delete/);
  assert.match(mergeRequest('gh pr merge 12 -ms').problem, /--merge/);
  assert.match(mergeRequest('gh pr merge --merge --subject 12 99').problem, /one pull request/);
  assert.match(mergeRequest('gh pr merge 12 --merge -R other/repo').problem, /repo/);
  assert.match(mergeRequest('gh pr merge 12 --merge --repo=other/repo').problem, /repo/);
  assert.match(mergeRequest('gh pr merge 12 -m -Rother/repo').problem, /repo/);
});

test('only the exact shape gh pr merge <number> --merge is allowed', () => {
  assert.deepEqual(mergeRequest('gh pr merge --merge 12'), { pr: '12', problem: null });
  for (const cmd of [
    'gh pr merge --merge --subject 12 other-branch',
    'gh pr merge --merge --subject 12 https://github.com/o/r/pull/99',
    'gh pr merge 12 --merge --body x',
    'gh pr merge 12 --merge feat/x',
  ]) assert.match(mergeRequest(cmd).problem, /only/, cmd);
  for (const cmd of [
    'gh pr merge --merge # 12',
    'gh pr merge 12 --merge $(echo --admin)',
    'gh pr merge 12 --merge `echo -d`',
    'gh pr merge 12 --merge --ad`min',
    'gh pr merge 12 --merge > out.txt',
  ]) assert.match(mergeRequest(cmd).problem, /shell/, cmd);
});

const GATE = 'review-gates: spec-review=pass security-review=pass tests=pass';
const goodPr = () => ({
  state: 'OPEN', isDraft: false, baseRefName: 'main', headRefName: 'feat/x',
  statusCheckRollup: [
    { __typename: 'CheckRun', name: 'python', status: 'COMPLETED', conclusion: 'SUCCESS' },
    { __typename: 'CheckRun', name: 'frontend', status: 'COMPLETED', conclusion: 'SKIPPED' },
  ],
  commits: [{ committedDate: '2026-11-14T10:00:00Z' }, { committedDate: '2026-11-14T11:00:00Z' }],
  comments: [{ body: `all checks done\n${GATE}`, createdAt: '2026-11-14T11:05:00Z' }],
});

test('merge gate passes only when every condition holds', () => {
  assert.equal(checkMergeGate(goodPr(), true), null);
  assert.match(checkMergeGate(goodPr(), false), /latest main/);
  assert.match(checkMergeGate({ ...goodPr(), state: 'MERGED' }, true), /open/);
  assert.match(checkMergeGate({ ...goodPr(), isDraft: true }, true), /draft/);
  assert.match(checkMergeGate({ ...goodPr(), baseRefName: 'feat/y' }, true), /main/);
  assert.match(checkMergeGate({ ...goodPr(), statusCheckRollup: [] }, true), /no CI/);
  const failing = goodPr();
  failing.statusCheckRollup[0].conclusion = 'FAILURE';
  assert.match(checkMergeGate(failing, true), /python/);
  const running = goodPr();
  running.statusCheckRollup[0] = { __typename: 'CheckRun', name: 'python', status: 'IN_PROGRESS', conclusion: null };
  assert.match(checkMergeGate(running, true), /python/);
  const statusCtx = goodPr();
  statusCtx.statusCheckRollup.push({ __typename: 'StatusContext', context: 'ext', state: 'PENDING' });
  assert.match(checkMergeGate(statusCtx, true), /ext/);
  assert.match(checkMergeGate({ ...goodPr(), comments: [] }, true), /gate record/);
  const stale = goodPr();
  stale.comments[0].createdAt = '2026-11-14T10:30:00Z'; // before the last commit
  assert.match(checkMergeGate(stale, true), /gate record/);
  const partial = goodPr();
  partial.comments[0].body = 'review-gates: spec-review=pass security-review=fail tests=pass';
  assert.match(checkMergeGate(partial, true), /gate record/);
});

test('gh pr merge is no longer blocked by the static rules (the gate decides)', () => {
  allowed('gh pr merge 12 --merge');
});

test('a pull request merge in any other form is blocked, because the gate checks only the plain form', () => {
  for (const cmd of [
    'GH_DEBUG=1 gh pr merge 12 --squash',
    'GH_REPO=o/r gh pr merge 12 --merge',
    'env gh pr merge 12 --squash',
    'env -i GH_TOKEN=x gh pr merge 12 --merge',
    'command gh pr merge 12 --squash',
    'gh.exe pr merge 12 --squash',
    '/usr/bin/gh pr merge 12 --squash',
    'C:\\tools\\gh.exe pr merge 12 --merge',
    'bash -c "gh pr merge 12 --squash"',
    'bash -c "gh pr merge 12 --merge"',
    'powershell -Command "gh pr merge 12 --merge"',
    'gh pr -R o/r merge 12 --squash',
    'gh pr --repo o/r merge 12',
    'gh api -X PUT repos/o/r/pulls/12/merge -f merge_method=squash',
    'gh api graphql -f query="mutation { mergePullRequest(input: {}) { clientMutationId } }"',
  ]) blocked(cmd);
  allowed('gh pr view 12 --json state');
  allowed('gh pr create --title merge --body x');
  allowed('gh api repos/o/r/pulls/12');
  allowed('bash -c "gh pr view 12"');
  allowed('git merge origin/main');
});

test('merge gate: changes to the shared queue are merged by a person only', () => {
  const pr = goodPr();
  pr.files = [{ path: 'src/a.py' }];
  assert.equal(checkMergeGate(pr, true), null);
  pr.files.push({ path: '.autopilot/queue.md' });
  assert.match(checkMergeGate(pr, true), /queue/);
});
