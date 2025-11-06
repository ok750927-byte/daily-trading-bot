# Secret rotation & incident response (quick guide)

This document describes steps to rotate compromised credentials found in `secrets.json` and to safely remove them from the repository history.

IMPORTANT: History rewriting is destructive — coordinate with all collaborators before force-pushing.

1) Immediate actions (do now)
 - Revoke/rotate all credentials contained in `secrets.json` (API keys, app secrets, account numbers) with their provider(s).
 - If any credentials were used in production, consider additional mitigation (freeze accounts, audit recent activity).

2) Local repository cleanup (already partially executed)
 - We have removed `secrets.json` from the current index and created a local backup: `secrets.json.local.bak`.
 - We also executed a local history rewrite to remove `secrets.json` from every commit (using git-filter-repo). This rewrites commit IDs locally.

3) Push/remote coordination (required to remove secrets there too)
 - After rotation, to remove secrets from the remote repo you must force-push the rewritten history.
 - All collaborators must re-clone the repository after the force-push or reset their local branches carefully.

 Recommended push sequence (run after team approval):
 ```
 git remote set-url origin <your-remote-url>  # ensure correct remote
 git push --force --all
 git push --force --tags
 ```

4) Validation
 - Check remote web UI to confirm `secrets.json` no longer appears in history or files list.
 - Run `git fsck` and `git log --stat` to validate.

5) Prevent future leaks
 - Keep `secrets.json` out of the repo. Use `secrets.sample.json` with placeholders.
 - Use environment variables, OS keyring, or a secrets manager (Vault, GitHub Secrets) for production credentials.
 - Add pre-commit hooks to block common secret patterns (e.g., `detect-secrets`, `git-secrets`).

6) Recovery checklist
 - Revoke and recreate keys.
 - Update CI secret stores with new keys.
 - Notify stakeholders if any live keys were exposed.

If you want, I can perform the force-push (optionally) after you confirm you have rotated keys and informed collaborators.
