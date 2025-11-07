# Broker Staging Guide

This document describes a safe, repeatable process for staging broker integration
before moving to production. It companionizes the `scripts/staging_broker_test.py`
template in the repository.

## Goals

- Verify end-to-end order submission and reconciliation in a staging environment.
- Confirm credentials and permissions are correct.
- Ensure idempotency and reconciliation logic behave as expected.

## Prerequisites

- A staging/test broker account (do not use production credentials for staging).
- Broker adapter factory implemented in `src/trading` (e.g. `KoreaInvestmentAdapter.from_env()`).
- CI and developer machine should have secrets configured for staging under safe scope.

## Steps

1. Implement real broker adapter factory
   - Add an adapter class `KoreaInvestmentAdapter` in `src/trading/broker_adapter.py` or a new module.
   - Provide a `from_env()` classmethod to read staging credentials from environment variables or keyring.

2. Test with DryRunAdapter (safe simulation)
   - Run:

```bash
python scripts/staging_broker_test.py --dry-run
```

   - Review `results/order_log.jsonl` and the reconciliation report printed to stdout.

3. Prepare staging credentials
   - Store keys in OS keyring or `secrets.json` per your operational policy.
   - Ensure the adapter `from_env()` reads staging-only secrets and not production secrets.

4. Run real broker test (manual and supervised)

```bash
python scripts/staging_broker_test.py --use-real-broker
```

   - This will attempt to use the real adapter. The script will currently raise an error
     unless you implement `load_real_broker()` or a proper factory as noted above.

5. Reconcile and review
   - Confirm the reconciliation report shows no mismatches or acceptable discrepancies.
   - If mismatches occur, inspect `results/order_log.jsonl` and the broker's order history.

6. Clean up
   - Cancel test orders in the broker staging UI if needed.
   - Revoke staging credentials or rotate keys per your security policy.

## Notes

- Always perform real-broker tests during low market-activity windows and with small notional sizes.
- Keep all staging artifacts and logs under restricted access control; avoid uploading these artifacts to shared public locations.
- Consider adding a dedicated GitHub Actions workflow in a protected branch for running staging smoke-tests with manual approval.
