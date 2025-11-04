"""
Approval manager for non-blocking operator approvals.

Features:
- submit requests (returns request_id)
- list pending requests
- approve/reject requests (writes audit log and notifies handler)

This is intentionally simple and thread-safe using a background worker and a
callable handler that will be invoked when a request is approved.
"""
from __future__ import annotations
import threading
import time
import json
import os
import uuid
from typing import Callable, Dict, Optional
import os
import threading
import requests

AUDIT_PATH = os.path.join(os.getcwd(), 'results', 'approval_audit.jsonl')
QUEUE_PATH = os.path.join(os.getcwd(), 'results', 'approval_queue.jsonl')
os.makedirs(os.path.dirname(AUDIT_PATH), exist_ok=True)


class ApprovalManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._pending: Dict[str, dict] = {}
        self._handler: Optional[Callable[[dict], None]] = None

    def register_handler(self, fn: Callable[[dict], None]):
        """Register a callable that will be invoked with the request dict when a request is approved."""
        self._handler = fn

    def submit(self, sig: dict) -> str:
        req_id = str(uuid.uuid4())
        rec = {
            'id': req_id,
            'signal': sig,
            'timestamp': int(time.time()),
            'status': 'pending'
        }
        with self._lock:
            self._pending[req_id] = rec
        # persist queue entry
        try:
            with open(QUEUE_PATH, 'a', encoding='utf-8') as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + '\n')
        except Exception:
            pass
        # notify via webhook if configured (do not include raw secrets)
        try:
            webhook = os.environ.get('APPROVAL_WEBHOOK_URL')
            if webhook:
                payload = {
                    'event': 'approval_requested',
                    'id': req_id,
                    'signal': {k: ('***MASKED***' if any(x in k.lower() for x in ('secret','token','password','key')) else v) for k,v in (sig.items() if isinstance(sig, dict) else [])},
                    'timestamp': rec['timestamp']
                }
                # fire-and-forget to avoid blocking submit
                threading.Thread(target=lambda: requests.post(webhook, json=payload, timeout=5), daemon=True).start()
        except Exception:
            pass
        return req_id

    def list_pending(self) -> Dict[str, dict]:
        with self._lock:
            return dict(self._pending)

    def approve(self, req_id: str, approver: Optional[str] = None, approve: bool = True):
        with self._lock:
            rec = self._pending.get(req_id)
            if not rec:
                return False
            rec['status'] = 'approved' if approve else 'rejected'
            rec['approved_by'] = approver
            rec['approved_at'] = int(time.time())
        # write audit
        # mask sensitive fields before writing audit
        def _mask_signal(sig: dict) -> dict:
            if not isinstance(sig, dict):
                return sig
            out = {}
            for k, v in sig.items():
                lk = k.lower()
                if any(x in lk for x in ('secret', 'token', 'password', 'key', 'app_secret')):
                    out[k] = '***MASKED***'
                elif 'account' in lk or 'no' in lk and isinstance(v, (str, int)):
                    s = str(v)
                    if len(s) > 4:
                        out[k] = s[:2] + '...' + s[-2:]
                    else:
                        out[k] = '***'
                else:
                    out[k] = v
            return out

        audit = {
            'id': req_id,
            'signal': _mask_signal(rec.get('signal')),
            'approved': bool(approve),
            'approver': approver,
            'ts': rec.get('approved_at')
        }
        try:
            with open(AUDIT_PATH, 'a', encoding='utf-8') as fh:
                fh.write(json.dumps(audit, ensure_ascii=False) + '\n')
        except Exception:
            pass

        # notify handler asynchronously if approved
        if approve and self._handler:
            try:
                threading.Thread(target=self._handler, args=(rec,), daemon=True).start()
            except Exception:
                pass

        # send webhook notification on decision
        try:
            webhook = os.environ.get('APPROVAL_WEBHOOK_URL')
            if webhook:
                payload = {
                    'event': 'approval_decision',
                    'id': req_id,
                    'approved': bool(approve),
                    'approver': approver,
                    'timestamp': rec.get('approved_at')
                }
                threading.Thread(target=lambda: requests.post(webhook, json=payload, timeout=5), daemon=True).start()
        except Exception:
            pass

        # remove from pending after decision
        with self._lock:
            self._pending.pop(req_id, None)

        return True
