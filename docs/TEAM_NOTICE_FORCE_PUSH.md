# Team notice: planned history rewrite (force-push)

Summary
-------
We plan to rewrite repository history to remove sensitive file(s) (example: `secrets.json`) from past commits and replace the remote history with a cleaned version. This is disruptive and requires coordination.

High-level timeline (example)
- T-48h: Notify team, rotate critical keys (broker, Discord), update CI secrets (required).
- T-2h: Final smoke tests with new keys (operator).
- T: Execute force-push (operator).
- T+1h: Validation and developer re-sync window.

Pre-conditions (MUST be completed before the force-push)
-----------------------------------------------------
- All exposed credentials rotated and new values stored in CI and keyring.
- Team acknowledgement received (reply-all or Slack confirmation).
- A maintenance window scheduled and recorded.

What you must do BEFORE the force-push
--------------------------------------
1) Secure your uncommitted work:

    - Stash or copy any uncommitted changes. Example:

       ```bash
       git status --porcelain
       git stash push -m "WIP before history rewrite"
       ```

2) If you have local branches not pushed to remote, push them to a temporary remote or save patches:

    ```bash
    git format-patch origin/main..HEAD -o ~/patches-before-rewrite
    ```

3) Confirm you have rotated keys (use `docs/KEY_ROTATION_TEMPLATES.md`). Reply to the team notice with a short confirmation: "I have rotated keys and updated CI secrets — ready."

What will happen during the force-push (brief)
---------------------------------------------
- The canonical repo will be replaced with the rewritten history. Commit SHAs will change. Branch references will be overwritten.

What you must do AFTER the force-push
-------------------------------------
Option A (recommended, clean): re-clone the repository

   ```bash
   # remove or move your current clone
   cd ..
   mv my-repo my-repo-backup
   git clone <repo-url> my-repo
   ```

Option B (advanced, keep local branches)

   ```bash
   git fetch --all --prune
   # reset local branch to match origin
   git checkout main
   git reset --hard origin/main
   # for feature branches, rebase onto updated main
   git checkout my-feature
   git rebase origin/main
   ```

If you had stashed work, re-apply it carefully and test locally before pushing.

Contact & rollback plan
-----------------------
- Contact: @team-lead (replace with actual Slack/Email) and ops on-call.
- Rollback: if the force-push causes immediate critical failures, we will restore from the pre-rewrite backup (operator has a local mirror and can restore the previous state). This is why we ask everyone to backup work.

Questions or objections
----------------------
If you are not ready or have concerns, reply to this notice BEFORE the scheduled window. Do NOT attempt to push during the maintenance window unless instructed.

-- End of notice --
