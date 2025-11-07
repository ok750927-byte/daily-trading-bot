Detected secrets scan report

The following potential secrets were found by `detect-secrets` when generating `.secrets.baseline`.
These entries are from `./.secrets.baseline` (version 1.5.0).

Findings:

- build/daily_trading_gui/EXE-00.toc (Hex High Entropy String) — line 25
  - hashed_secret: 1f0e0bc8d92f1418d08159273ef8f9697ce9ba16
  - Likely: binary build artifact; consider removing build/ from repo and adding to .gitignore

- docs/DEPLOY.md (Secret Keyword) — line 19
  - hashed_secret: 29c32f233d04598b3181c0e27ea0ec7a5c949297
  - Action: inspect the file; if this is a real secret, remove and rotate; else mark as false positive or redact.

- secrets.sample.json (Secret Keyword) — line 3
  - hashed_secret: 6edb6f146bab0399222bfd1c8e225eaa9651cff9
  - Action: this is a sample file; ensure it contains only placeholders. Replace real values with placeholders and update README.

- tests/test_korea_investment_monitor.py (Secret Keyword) — line 7
  - hashed_secret: 829c3804401b0727f70f73d4415e162400cbe57b
  - Action: tests may contain example credentials; redact or use environment variables / fixtures.

- tests/test_korea_investment_order.py (Secret Keyword) — line 12
  - hashed_secret: 829c3804401b0727f70f73d4415e162400cbe57b
  - Action: same as above; unify with test fixtures or mocks.

Next recommended steps

1) Review each listed file and decide whether the flagged content is a true secret.
   - If true secret: remove it from the file, rotate the secret (reissue key/password), and plan a git history rewrite if the secret existed in past commits.
   - If false positive or sample placeholder: add an inline `# pragma: allowlist secret` comment (for code lines) or remove from scan via baseline filters.

2) For binary artifacts (build/*) remove them from the repository and add to `.gitignore`. Rebuild artifacts should not be tracked.

3) If you choose to purge secrets from history, we can prepare a `git-filter-repo` plan and the exact list of strings to remove. This requires team coordination and force-push.

4) After cleaning/remediation or baseline acceptance, run `pre-commit run --all-files` locally, commit any hook-applied fixes, then push so CI can pass.

If you want, I can:
- Open each file and show the flagged lines (with context) so you can confirm whether they're real secrets.
- Prepare a git-filter-repo commands file to purge secrets when you approve.
- Apply replacements (redaction) and commit, then run history rewrite with your confirmation.
