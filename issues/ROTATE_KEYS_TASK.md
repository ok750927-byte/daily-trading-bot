# Issue: Rotate exposed keys and update CI / re-sync team

**Note:** The keys currently found in the repository are known to be paper/sandbox credentials. This issue remains as a checklist and audit trail; priority can be set to Low if no production keys are affected. If any non-sandbox keys are discovered, escalate to High and follow the revocation steps below.

Summary
 # Issue: Rotate exposed keys and update CI / re-sync team

 Summary
 -------
 This issue coordinates revocation and rotation of any credentials that were found in `secrets.json` (or elsewhere in the repository/workspace), updates CI/CD secrets, verifies systems, and documents the operation for audit and follow-up.

 Impact
 ------
 - Services potentially affected: trading broker(s), market data providers, notification/webhook endpoints (Discord), CI pipelines, local developer environments.
 - Priority: High — rotate and revoke exposed keys immediately to prevent abuse.

 Goals
 -----
 1. Revoke exposed credentials at their providers.
 2. Create and store new credentials in the team's secret store (GitHub Actions secrets, Vault, or equivalent).
 3. Update CI/CD and any deployment secrets with the new credentials.
 4. Validate application behavior in staging and production (smoke tests).
 5. Document actions, timestamps, and confirmations for audit.

 Checklist (actionable)
 ----------------------
 - [ ] List all exposed secrets here (name, provider, file/path, sample masked value):
			 - e.g. `KIS_APP_KEY` (broker) — found in `secrets.json` — last 4 chars: `****o72U7s7`
 - [ ] For each secret: Revoke the old credential at the provider and record the revocation timestamp and confirmation ID.
 - [ ] Create new credentials and securely store them in the team's secret manager (GitHub Actions secrets or Vault). Do NOT commit new secrets into the repo.
 - [ ] Replace local copies: update `secrets.json.local.bak` (for reference) and move dev workflows to use OS keyring / environment variables where possible.
 - [ ] Update CI secrets using provided scripts: `scripts/gh_set_secrets_examples.sh` or `scripts/gh_set_secrets_examples.ps1` (or use `gh secret set`).
 - [ ] Run staging smoke tests and sanity checks. Confirm no critical regressions.
 - [ ] Notify team (Slack/Email) with the list of rotated secrets, impact, and required actions.
 - [ ] Schedule and perform optional repo history cleanup only after all keys are revoked and new keys are verified.

 Provider-specific rotation steps (examples)
 -----------------------------------------
 These are generic steps — adapt to each provider's dashboard/API.

 Broker (example: KIS or other trading broker)
 - Login to broker developer console.
 - Revoke the exposed API key / app secret.
 - Create a new API key/secret pair.
 - Update CI secret (example using gh):
	 ```cmd
	 gh secret set KIS_APP_KEY --body "<new-key>" --repo ok750927-byte/daily-trading-bot
	 gh secret set KIS_APP_SECRET --body "<new-secret>" --repo ok750927-byte/daily-trading-bot
	 ```
 - Update staging config and run smoke tests.

 Notification/Webhooks (Discord or similar)
 - Revoke or rotate the webhook token/URL in the service.
 - Update CI and runtime environment variables with the new webhook URL.

 GitHub Actions / CI
 - Prefer repository secrets: `Settings -> Secrets and variables -> Actions` (or use `gh secret set`).
 - Example: update secret via script (Linux/macOS/WSL / PowerShell recommended for Windows):
	 ```bash
	 ./scripts/gh_set_secrets_examples.sh ok750927-byte/daily-trading-bot
	 ```
 - Or use `gh secret set SECRET_NAME --repo owner/repo --body "value"` for each secret.

 Local developer guidance
 - Do NOT commit secrets to the repository. Use `secrets.sample.json` for placeholders.
 - For local testing, prefer using OS keyring (keyring libraries) or local environment variables managed per-developer.

 Verification checklist (post-rotation)
 ------------------------------------
 - [ ] Each provider confirms revocation (screenshot/confirmation ID attached).
 - [ ] CI secrets updated and deployments succeed.
 - [ ] Staging smoke tests pass (list test names and timestamps).
 - [ ] Production smoke/health checks pass within maintenance window.
 - [ ] No unexpected errors in logs related to authentication or webhook failures for 24 hours.

 Commands & quick helpers
 ------------------------
 - Create/update a GitHub Actions secret (example):
	 ```cmd
	 gh secret set SECRET_NAME --repo ok750927-byte/daily-trading-bot --body "<value>"
	 ```
 - Run the provided update script (if executable):
	 ```bash
	 bash ./scripts/gh_set_secrets_examples.sh ok750927-byte/daily-trading-bot
	 ```
 - Run smoke tests (example, run unit tests or a minimal smoke runner):
	 ```bash
	 pytest tests/smoke_tests.py::test_connects_to_broker -q
	 ```
	 (Adapt to project's test targets and environment)

 Team notification templates
 --------------------------
 Short Slack/Chat template
 ```text
 Heads-up: We discovered committed credentials and are rotating them now. Impact: short maintenance window for CI/deployments. Actions taken: revoked exposed keys, creating new keys, updating CI secrets. If you see failures, please alert #ops immediately. More details: <link to this issue>
 ```

 Email template (detailed)
 ```text
 Subject: URGENT: Rotate exposed API keys — action required

 Team,

 We found API credentials committed in the repository. We are revoking the exposed credentials now and will replace them with new ones. Please do not use the old keys. Actions and timeline:
 - Revoke and rotate keys (completed by ops) — T+0
 - Update CI secrets and redeploy to staging — T+15 minutes
 - Run smoke tests and validate — T+30 minutes
 - If validated, schedule production update and optional repo history cleanup — T+60 minutes

 See details and checklist: <link to this issue>

 Regards,
 Security/Ops
 ```

 Rollback plan
 -------------
 - If new keys cause unexpected failures, revert CI secret to a previously known-good credential only if that credential is still valid and permitted by security policy (prefer manual intervention and communication).
 - Prefer controlled rollback window and temporary feature freeze for trading to avoid unintended orders.

 Post-incident activities
 ------------------------
 - Publish a short postmortem in `docs/` containing: timeline, root cause, impacted systems, lessons learned, and follow-ups (e.g., stricter CI checks, pre-commit hooks).
 - Ensure `.pre-commit-config.yaml` includes detect-secrets and other static checks.

 Assignee: @ops (replace with actual user or team)
 Priority: High

 Labels (suggested): security, incident, high, needs-audit

 Notes
 -----
 Keep a secure offline record of old keys only until provider confirms revocation. After revocation, delete insecure copies. All steps that touch credentials must use secure channels and should be logged (timestamp + actor).

 ```
