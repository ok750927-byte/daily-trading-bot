"""CI helper: verify cryptography lib can generate and verify an ECDSA signature.

Exits 0 on success, non-zero on failure.
"""
from __future__ import annotations
import sys

try:
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.backends import default_backend
except Exception as e:
    print('cryptography import failed:', e)
    raise SystemExit(2)

try:
    priv = ec.generate_private_key(ec.SECP256R1(), default_backend())
    pub = priv.public_key()
    msg = b'test-crypto'
    sig = priv.sign(msg, ec.ECDSA(hashes.SHA256()))
    pub.verify(sig, msg, ec.ECDSA(hashes.SHA256()))
    print('ECDSA generate+verify OK')
    raise SystemExit(0)
except Exception as e:
    print('ECDSA test failed:', e)
    raise SystemExit(1)
