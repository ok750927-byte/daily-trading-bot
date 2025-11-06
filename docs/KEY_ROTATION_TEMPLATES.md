# Key rotation templates

This file contains short templates and commands to help rotate commonly used secrets found in this project.

1) Broker API (example: KIS / KOREA broker)

- Action: Revoke existing app key/secret in broker developer console and create a new key.
- Notify: update `secrets.json.local.bak` (local secure store) and CI secrets (GitHub Actions secrets) with the new values.

Template message to broker admin (if needed):

```
Subject: Request to rotate API key for account <ACCOUNT_NUMBER>

Please revoke API key <old_key_redacted> and issue a new API key and secret for account <ACCOUNT_NUMBER>.
Reason: credential exposure in local repository history.

Please provide new key/secret and confirm old key was revoked.
```

2) Discord webhook

- Action: In Discord channel settings -> Integrations -> Webhooks, delete the existing webhook and create a new one. Replace `DISCORD_WEBHOOK_URL` in CI secrets.

Template internal note:

```
Discord webhook rotated: old webhook deleted; new webhook stored in CI secret: DISCORD_WEBHOOK_URL
```

3) GitHub Actions / CI secrets

- Action: Go to repository Settings -> Secrets and variables -> Actions -> New repository secret. Create entries for each rotated secret (e.g., KIS_APP_KEY, KIS_APP_SECRET, DISCORD_WEBHOOK_URL).

4) After rotation

- Update local development: store new secrets in OS keyring or local `.env` (do NOT commit), or update `secrets.json.local.bak` stored offline.
- Run a quick smoke test (or CI run) to ensure credentials work.
