"""Verify the approval audit JSONL log integrity using the chained SHA256 hashes.

Usage:
  python scripts/verify_audit_log.py results/approval_audit.jsonl

Exit codes:
  0 - OK
  1 - mismatch found or file error
"""
from __future__ import annotations

import argparse
import json
import sys
import hashlib
from pathlib import Path
from src.trading import operator_auth
try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.exceptions import InvalidSignature
    CRYPTO_AVAILABLE = True
except Exception:
    CRYPTO_AVAILABLE = False


def compute_hash(entry: dict) -> str:
    # compute hash deterministically using sorted keys and ensure_ascii=False
    return hashlib.sha256(json.dumps(entry, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()


def verify(path: Path) -> int:
    if not path.exists():
        print(f"File not found: {path}")
        return 1
    prev_hash = ''
    with path.open('r', encoding='utf-8') as fh:
        line_no = 0
        for line in fh:
            line_no += 1
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except Exception as e:
                print(f"Line {line_no}: invalid JSON: {e}")
                return 1
            expected_prev = entry.get('prev_hash', '')
            if expected_prev != prev_hash:
                print(f"Line {line_no}: prev_hash mismatch (expected '{prev_hash}', found '{expected_prev}')")
                return 1
            # entry copy without the 'hash' field for recomputation
            actual_hash = entry.get('hash', '')
            entry_copy = dict(entry)
            # ensure 'hash' exists in entry_copy when computing, remove it to compute
            entry_copy.pop('hash', None)
            # compute hash over the canonical form
            recomputed = compute_hash(entry_copy)
            if recomputed != actual_hash:
                print(f"Line {line_no}: hash mismatch (computed '{recomputed}', recorded '{actual_hash}')")
                return 1
            # if there's a signature and approver, try to verify it
            sigobj = entry.get('signature')
            approver = entry.get('approver')
            if sigobj and approver:
                method = sigobj.get('method') if isinstance(sigobj, dict) else None
                recorded = sigobj.get('sig') if isinstance(sigobj, dict) else None
                # prefer public key for verification
                pub = operator_auth.get_public_key(approver)
                if method == 'ecdsa-sha256' and pub and CRYPTO_AVAILABLE:
                    try:
                        public_key = serialization.load_pem_public_key(pub.encode('utf-8'))
                        sig_input = dict(entry)
                        sig_input.pop('hash', None)
                        sig_input.pop('signature', None)
                        canonical_sig = json.dumps(sig_input, sort_keys=True, ensure_ascii=False).encode('utf-8')
                        sig_bytes = bytes.fromhex(recorded)
                        public_key.verify(sig_bytes, canonical_sig, ec.ECDSA(hashes.SHA256()))
                    except InvalidSignature:
                        print(f"Line {line_no}: signature verification FAILED for approver '{approver}'")
                        return 1
                    except Exception as e:
                        print(f"Line {line_no}: signature verification error: {e}")
                        return 1
                else:
                    # no public key available; try legacy key retrieval (private PEM in keyring) fallback
                    key = operator_auth.get_signing_key(approver)
                    if key:
                        # legacy PBKDF2-based signature (support older entries)
                        sig_input = dict(entry)
                        sig_input.pop('hash', None)
                        sig_input.pop('signature', None)
                        canonical_sig = json.dumps(sig_input, sort_keys=True, ensure_ascii=False)
                        recomputed_sig = hashlib.pbkdf2_hmac('sha256', canonical_sig.encode('utf-8'), key.encode('utf-8'), 1000).hex()
                        if recorded != recomputed_sig:
                            print(f"Line {line_no}: legacy signature verification failed for approver '{approver}'")
                            return 1
            prev_hash = actual_hash
    print("Audit log verified: chain OK")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('path', nargs='?', default='results/approval_audit.jsonl')
    args = parser.parse_args(argv)
    return verify(Path(args.path))


if __name__ == '__main__':
    raise SystemExit(main())
