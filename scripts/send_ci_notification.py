"""Send a simple CI notification to a webhook (Discord/Slack compatible).

Usage:
  python scripts/send_ci_notification.py --webhook "$WEBHOOK_URL" --message "Build failed"

The script posts a small JSON payload. For Slack, use an Incoming Webhook URL.
For Discord, use a webhook URL and it will accept the same JSON (content).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


def send_webhook(url: str, payload: dict) -> int:
    data = json.dumps(payload).encode('utf-8')
    req = Request(url, data=data, headers={'Content-Type': 'application/json'})
    try:
        with urlopen(req, timeout=10) as resp:
            resp.read()
        return 0
    except HTTPError as e:
        print('HTTPError:', e.code, e.reason)
        return 2
    except URLError as e:
        print('URLError:', e.reason)
        return 3


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--webhook', required=True, help='Webhook URL')
    parser.add_argument('--failed-jobs', default='', help='Comma-separated list of failed jobs')
    parser.add_argument('--repo', default=os.environ.get('GITHUB_REPOSITORY', ''), help='Repository name')
    parser.add_argument('--run-id', default=os.environ.get('GITHUB_RUN_ID', ''), help='GitHub Actions run id')
    args = parser.parse_args(argv)

    repo = args.repo
    run_id = args.run_id
    failed_jobs = args.failed_jobs

    url = f'https://github.com/{repo}/actions/runs/{run_id}' if repo and run_id else ''

    content = f'CI failure in {repo}. Failed jobs: {failed_jobs}. {url}'
    payload = {
        'content': content
    }

    return send_webhook(args.webhook, payload)


if __name__ == '__main__':
    raise SystemExit(main())
