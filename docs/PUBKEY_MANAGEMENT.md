# Operator Public Key Management

This document explains how operator public keys are collected and made available
for audit verification (`scripts/verify_audit_log.py`). The repository stores
public keys in `results/operator_pubkeys.json` when created via
`scripts/operator_set_creds.py`.

Recommendations

- Public keys are not secrets and may be archived with CI artifacts if your
  security policy allows, but restrict access to the artifact storage (private
  repository or protected artifact storage).
- Private keys must never be committed. Private keys are stored in the OS
  keyring by `operator_set_creds.py` (or in a Vault/HSM in production).
- CI verification uses `results/operator_pubkeys.json` (if present) to validate
  ECDSA signatures recorded in audit logs.

How to deploy public keys to CI runners

Option A (recommended for small teams):
1. After running `scripts/operator_set_creds.py`, copy `results/operator_pubkeys.json` to a secure location accessible by CI (example: encrypted S3 bucket, or GitHub Actions secret-managed artifact store).
2. In CI, download that file at the start of the workflow and place it into the repository workspace at `results/operator_pubkeys.json` before running `scripts/verify_audit_log.py`.

Option B (for fully automated infra):
- Use your secret manager or artifact storage to store public key files and configure CI to fetch them using authenticated credentials (CI machine identity). Keep the retrieval step behind branch protection / manual approval if required.

Example: simple GitHub Actions snippet to fetch a public-keys artifact (pseudo):

```yaml
- name: Download operator pubkeys (protected storage)
  run: |
    # e.g. aws s3 cp s3://my-secure-bucket/operator_pubkeys.json results/operator_pubkeys.json
    echo "(implement per your infra)"
```

Security notes

- Never store operator private keys in repo or in artifacts.
- Rotate operator keys on suspected compromise; provide a revocation process.
- Consider using a PKI with short-lived certificates for operators in high-security environments.
