# Key rotation templates & quick-playbook

This file provides concrete, provider-targeted rotation steps, quick verification commands, and ready-to-send templates to coordinate rotation after a secret exposure.

IMPORTANT: Always rotate (revoke + reissue) exposed credentials before performing any destructive repository operations (e.g., force-push that rewrites history).

---

## 1) Broker API (KIS / KOREA example)

Goal: Revoke the old key/secret pair and obtain a new pair, then update CI and local secure stores.

Steps (operator)
- 1. Log into broker developer console for the affected account.
- 2. Revoke/delete the existing API key(s) listed in `secrets.json`.
- 3. Create a new API key + secret pair; copy values to a secure vault or local encrypted file (do NOT commit).
- 4. Update CI secrets (see GitHub Actions section below) and OS keyring/local dev stores.
- 5. Run smoke tests in a staging environment to confirm the new credentials work.

Suggested operator message to broker support (if programmatic console is unavailable):

Subject: Request to rotate API key for account <ACCOUNT_NUMBER>

Please revoke API key `<old_key_redacted>` and issue a new API key and secret for account `<ACCOUNT_NUMBER>`.
Reason: credential exposure in repository history. Please confirm when the old key is revoked and provide the newly issued key/secret via our secure channel.

---

## 2) Discord webhook

Steps
- 1. In Discord -> Server Settings -> Integrations -> Webhooks: delete the old webhook for the channel.
- 2. Create a new webhook and copy its URL.
- 3. Update the CI secret `DISCORD_WEBHOOK_URL` (see GitHub Actions section) and any local dev stores.
- 4. Verify by sending a test payload (example with curl below).

Quick verification (replace URL):

```
curl -X POST -H "Content-Type: application/json" -d '{"content":"Webhook rotation test"}' https://discord.com/api/webhooks/<id>/<token>
```

---

## 3) GitHub Actions / CI secrets (how to update)

Preferred: use GitHub UI (Settings -> Secrets and variables -> Actions -> New repository secret).
Optional (CLI with `gh`):

```
# set a secret using GitHub CLI (requires gh auth)
gh secret set KIS_APP_KEY --body "<new_key>" --repo <owner>/<repo>
gh secret set KIS_APP_SECRET --body "<new_secret>" --repo <owner>/<repo>
gh secret set DISCORD_WEBHOOK_URL --body "https://discord.com/api/webhooks/<id>/<token>" --repo <owner>/<repo>
```

Notes
- Do not store secrets in files tracked by Git. Use the repository secret or organization-level secret scopes.
- After updating CI secrets, trigger a CI run (or push a test commit) to validate workflows.

---

## 4) Local developer guidance

- Preferred local store: OS keyring (the project already includes `src/trading/keychain.py` helpers). Use `keyring` package or `gh`/OS native storage.
- If you must keep a plaintext local file for convenience, use `secrets.json.local.bak` stored offline, encrypted, or in a restricted folder — do NOT commit it.

Example: set secret in keyring (python snippet)

```python
from src.trading.keychain import set_secret_in_keyring
set_secret_in_keyring('KIS_APP_KEY', '<new_key>')
set_secret_in_keyring('KIS_APP_SECRET', '<new_secret>')
```

---

## 5) Verification checklist (after rotation)

- [ ] Old keys revoked (provider confirms)
- [ ] New keys stored in CI secrets
- [ ] Local keyring updated (developer machines that need access)
- [ ] Smoke test passed in staging (API calls succeed)
- [ ] Logs reviewed for suspicious activity (time window prior to rotation)

If you want, I can generate the exact `gh` commands and a team-notice email body customized with repo and contact placeholders.
