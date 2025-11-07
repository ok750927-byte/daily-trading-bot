# Team notification templates for secret rotation & history rewrite

Use these templates to notify stakeholders by email or Slack before/after rotating keys and (optionally) force-pushing rewritten history.

---

## 1) Short email (pre-rotation)

Subject: URGENT: Rotate exposed API keys & planned repo maintenance window

Hi team,

We discovered exposed credentials in the repository history and will rotate the affected keys. Please follow the instructions below.

Planned maintenance window: [DATE and TIME, e.g., 2025-11-07 10:00 UTC]

Immediate actions required from developers:

- Confirm you have no uncommitted local work (stash or back it up).
- Rotate any personal/stored keys if you used the exposed credentials.

After rotation, we plan to perform a controlled repository history rewrite to remove the sensitive file(s). We will post another notice when the rewrite is complete.

Contact: [ops@company.com] or [Slack #ops]

Thanks,
Security/Operations

---

## 2) Slack message (pre-rotation)

Heads-up: We found exposed secrets in repo history. We'll rotate keys and perform a repo cleanup.

Please:
• Stash or backup any uncommitted work.
• Confirm you have rotated/stored new keys in the keyring/CI secrets.

Maintenance window: [DATE/TIME]. Contact: @ops

---

## 3) Email (post-rotation + instructions)

Subject: Completed: Key rotation & repo history cleanup

Hi team,

We have rotated the exposed credentials and completed the repository history rewrite to remove the sensitive files.

Post-cleanup actions for developers (choose one):

Option A (recommended): Re-clone repository
```bash
git clone <repo-url>
```

Option B (advanced): Reset your local branches
```bash
git fetch --all --prune
git checkout main
git reset --hard origin/main
```

If you have local changes, please restore them from your backups or patches created prior to the force-push.

Thanks — ops

---

Fill in the placeholders (DATE/TIME, contact, repo URL) before sending.
