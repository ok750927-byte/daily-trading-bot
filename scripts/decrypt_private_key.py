"""Decrypt a private key file written by `operator_set_creds.py` fallback.

Usage:
  python scripts/decrypt_private_key.py results/operator_privkeys.enc

The script will prompt for the passphrase and print the PEM to stdout (or write to a file if --out is provided).
"""
from __future__ import annotations
import argparse
import json
import sys
import base64

try:
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.fernet import Fernet
    CRYPTO_OK = True
except Exception:
    CRYPTO_OK = False


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('path', nargs='?', default='results/operator_privkeys.enc')
    parser.add_argument('--out', help='Write PEM to a file instead of stdout')
    args = parser.parse_args(argv)

    if not CRYPTO_OK:
        print('cryptography not installed; cannot decrypt')
        return 2

    try:
        with open(args.path, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
    except Exception as e:
        print('Failed to read file:', e)
        return 1

    passphrase = input('Passphrase to decrypt private key: ')
    if not passphrase:
        print('Passphrase required')
        return 2

    try:
        salt = base64.urlsafe_b64decode(data['salt'].encode('utf-8'))
        token = data['token'].encode('utf-8')
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=390000)
        key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode('utf-8')))
        f = Fernet(key)
        pem = f.decrypt(token).decode('utf-8')
    except Exception as e:
        print('Decryption failed:', e)
        return 1

    if args.out:
        with open(args.out, 'w', encoding='utf-8') as fh:
            fh.write(pem)
        print('Wrote PEM to', args.out)
    else:
        print(pem)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
