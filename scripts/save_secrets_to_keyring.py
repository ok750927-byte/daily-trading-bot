r"""
Utility to save environment secrets into the OS keyring for `daily_trading_bot` service.

Usage (Windows cmd):
    python scripts\save_secrets_to_keyring.py --set KOREA_APP_KEY=xxx --set KOREA_APP_SECRET=yyy

This script stores each key as the username and the secret as the password under
the service name 'daily_trading_bot'. It is intentionally simple and interactive
when values are not provided on the command line.
"""
from __future__ import annotations
import argparse
import getpass
import sys
from pathlib import Path


def main(argv=None):
    p = argparse.ArgumentParser(description='Save secrets into OS keyring for daily_trading_bot')
    p.add_argument('--set', action='append', default=[], help='Set a KEY=VALUE pair (can be repeated)')
    p.add_argument('--file', '-f', help='Load JSON file with key->value mapping')
    p.add_argument('--service', default='daily_trading_bot', help='Keyring service name')
    args = p.parse_args(argv)

    pairs = {}
    # parse --set KEY=VALUE pairs
    for s in args.set:
        if '=' not in s:
            print(f"무효한 --set 값(키=값 형식 필요): {s}")
            sys.exit(2)
        k, v = s.split('=', 1)
        pairs[k.strip()] = v

    # parse file if provided
    if args.file:
        import json
        pth = Path(args.file)
        if not pth.exists():
            print(f"파일이 없습니다: {args.file}")
            sys.exit(2)
        with pth.open('r', encoding='utf-8') as fh:
            data = json.load(fh)
        for k, v in data.items():
            pairs.setdefault(k, v)

    # interactive prompt for any common keys if not provided
    common_keys = ['KOREA_APP_KEY', 'KOREA_APP_SECRET', 'KOREA_ACCOUNT_NO', 'KOREA_ACCOUNT_PRDT']
    for k in common_keys:
        if k not in pairs:
            try:
                val = getpass.getpass(prompt=f'[{k}] 값을 입력하세요 (엔터로 건너뜀): ')
            except Exception:
                val = ''
            if val:
                pairs[k] = val

    if not pairs:
        print('저장할 시크릿이 없습니다. --set 또는 --file 옵션을 사용하거나 프롬프트에 값을 입력하세요.')
        return

    # store into keyring (import at runtime to avoid hard dependency on startup)
    try:
        import keyring
    except Exception:
        print('keyring 패키지가 설치되어 있지 않습니다. 먼저 pip install keyring를 실행하세요.')
        sys.exit(3)

    service = args.service
    for k, v in pairs.items():
        try:
            keyring.set_password(service, k, str(v))
            print(f'저장 완료: service={service} key={k}')
        except Exception as e:
            print(f'저장 실패: {k} ({e})')


if __name__ == '__main__':
    main()
