"""Mask or detect likely secrets in text files.

Usage:
  python scripts/mask_secrets.py file1.log file2.xml

The script replaces suspicious tokens with '***REDACTED***' in-place and
returns exit code 0 if no unmasked secrets remain, or 2 if masking performed,
or 3 if a fatal pattern was found (e.g., very long hex that looks like a private key).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Patterns to mask (simple heuristics)
from __future__ import annotations

import argparse
import base64
import re
import sys
from pathlib import Path

# Initial heuristic patterns
PATTERNS = [
    re.compile(r"gh[pso]_?[A-Za-z0-9_\-]{20,}"),                       # GitHub tokens (multiple prefixes)
    re.compile(r"AKIA[0-9A-Z]{16}"),                                    # AWS access key
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{8,}"),                          # Slack tokens
    re.compile(r"(?i)password\s*[:=]\s*\S+"),                         # password= or password: value
    re.compile(r"(?i)secret\s*[:=]\s*\S+"),                           # secret= or secret: value
    re.compile(r"[A-Fa-f0-9]{40,}"),                                    # long hex strings (potential keys)
]


def looks_like_base64(s: str) -> bool:
    s = s.strip()
    if len(s) < 40:
        return False
    try:
        base64.b64decode(s + '==')
        return True
    except Exception:
        return False


def scan_text_for_patterns(text: str):
    matches = []
    for p in PATTERNS:
        for m in p.finditer(text):
            matches.append(m.group(0))
    # JWT-like tokens
    for m in re.findall(r"([A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,})", text):
        matches.append(m)
    # long base64-like fragments
    for frag in re.findall(r"[A-Za-z0-9_\-\\+/=]{40,}", text):
        if looks_like_base64(frag):
            matches.append(frag)
    return list(dict.fromkeys(matches))


def mask_text(text: str, matches) -> str:
    for m in matches:
        text = text.replace(m, '***REDACTED***')
    return text


def process_file(path: Path, mask: bool = True):
    text = path.read_text(encoding='utf-8', errors='ignore')
    matches = scan_text_for_patterns(text)
    if not matches:
        return 0, []
    if mask:
        new_text = mask_text(text, matches)
        path.write_text(new_text, encoding='utf-8')
        return 2, matches
    return 3, matches


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('files', nargs='+')
    parser.add_argument('--fail-if-found', action='store_true', help='Fail (non-zero) if any likely secret patterns are found')
    parser.add_argument('--mask', action='store_true', help='Mask found patterns in-place (default if --fail-if-found not provided)')
    args = parser.parse_args(argv)

    overall_rc = 0
    for fn in args.files:
        path = Path(fn)
        if not path.exists():
            print(f'WARN: {fn} not found, skipping')
            continue
        if args.fail_if_found:
            rc, matches = process_file(path, mask=False)
            if rc != 0:
                print(f'SECRET PATTERNS FOUND in {fn}:')
                for m in matches[:10]:
                    print('  ', m)
                overall_rc = max(overall_rc, rc)
        else:
            rc, matches = process_file(path, mask=args.mask or True)
            if rc != 0:
                print(f'Masked {len(matches)} items in {fn}')
                overall_rc = max(overall_rc, rc)
    return overall_rc


if __name__ == '__main__':
    raise SystemExit(main())
