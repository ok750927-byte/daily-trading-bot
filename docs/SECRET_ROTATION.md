# Secret rotation & incident response (playbook)

This guide expands the quick steps for rotating compromised credentials, validating the rotation, and optionally removing secrets from remote history.

WARNING: History rewriting (force-push) is disruptive. Do NOT perform it until all exposed keys are revoked and the team is notified.

## A. Immediate operator checklist (first 1–2 hours)
- [ ] Identify all secrets exposed (scan `secrets.json` and recent commits).
- [ ] Revoke/rotate each secret with its provider (broker API keys, Discord webhook, DB passwords, etc.).
- [ ] Record rotation actions: timestamp, rotated key names, who performed it, and confirmation IDs from provider.
- [ ] If production keys were exposed: freeze accounts / enable MFA / audit recent API activity.

## B. Local repo state (what we've already done)
- The working tree had `secrets.json` committed. A local backup exists as `secrets.json.local.bak`.
- A local history rewrite was executed using `git-filter-repo` to remove `secrets.json` from prior commits. This changed local commit IDs.

Important: local rewrite DOES NOT affect remote until you push rewritten history (force-push).

## C. Remote cleanup (team coordination required)

Preconditions (must be satisfied before force-push):
- All exposed credentials rotated and new values stored in CI / keyring.
- Team notified and a maintenance window agreed.
- Backups of any important refs/tags made.

Recommended safe sequence to force-push (operator executing on the canonical machine):

1) Verify local tests and staging runs with new keys.
2) Push rewritten history (example):

```
# double-check remote
git remote -v
# push all branches and tags — THIS WILL REWRITE REMOTE HISTORY
git push --force --all origin
git push --force --tags origin
```

3) Post-push validation
- Confirm in GitHub/GitLab UI that `secrets.json` no longer appears in file tree or historical commits.
- Run spot checks with `git log --stat` and `git grep 'KIS_APP_KEY' $(git rev-list --all)` to ensure nothing remains.

## D. Roll-forward housekeeping
- Ask all developers to re-clone or reset local clones (see `docs/TEAM_NOTICE_FORCE_PUSH.md` for instructions).
- Update release processes or CI that referenced old commit hashes.

## E. Preventive controls (long-term)
- Enforce pre-commit `detect-secrets` in local hooks and CI scan jobs.
- Centralize secret loading: prefer OS keyring / env vars / secrets manager. Replace ad-hoc `secrets.json` usage with a loader that reads from keyring or env.
- Add periodic secret rotation policy (e.g., every 90 days) and automated test that fails if secrets are found in diffs.

## F. Quick verification commands (examples)

Search for strings across all historical commits (post-rewrite validation):

```
# check for a known secret pattern across all objects
git rev-list --all | xargs git grep -F "KIS_APP_KEY" --no-index || true
```

Check remote history for file name:

```
# check web UI, and also fetch and ensure no refs show the file
git fetch origin --prune
git log --all --name-only | grep secrets.json || true
```

## G. Recovery checklist (final)
- [ ] Confirm old keys revoked and inaccessible
- [ ] Confirm new keys are stored in CI and keyring
- [ ] Confirm remote no longer contains `secrets.json` in history
- [ ] Confirm all devs re-cloned or reset local branches
- [ ] Monitor logs for suspicious activity for 48–72 hours

If you'd like, I can generate a step-by-step script to (A) rotate provider keys (templates + contact text), (B) run the final verification commands, and (C) perform the force-push once you explicitly approve.
