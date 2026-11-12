`guard.mjs` is based on `skills/misc/git-guardrails-claude-code/scripts/block-dangerous-git.sh` from
https://github.com/mattpocock/skills (commit 5863806), copyright Matt Pocock, MIT licence:

> Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
> documentation files (the "Software"), to deal in the Software without restriction, including without limitation
> the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
> permit persons to whom the Software is furnished to do so, subject to the following conditions: The above copyright
> notice and this permission notice shall be included in all copies or substantial portions of the Software.
> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.

Changes: rewritten in Node (no jq); `git push` is allowed for task branches; added blocks for pushing or merging into
`main`, `gh pr merge`, force pushes of any kind, remote branch deletion, and recursive deletes outside scratch
folders (Bash and PowerShell). Kept from the original: `git reset --hard`, `git clean -f`, `git branch -D`,
`git checkout .`, `git restore .`.

Tests: `node --test .claude/hooks/guard.test.mjs`.
