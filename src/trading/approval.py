from __future__ import annotations

import json
import threading
import time
import uuid
import os
from pathlib import Path
from typing import Callable, Dict, Optional, List, Any

ROOT = Path(__file__).parent.parent
RESULTS_DIR = ROOT / 'results'
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
PENDING_FILE = RESULTS_DIR / 'pending_approvals.jsonl'
AUDIT_FILE = RESULTS_DIR / 'approval_audit.jsonl'
QUEUE_FILE = RESULTS_DIR / 'approval_queue.jsonl'


# helper: mask sensitive fields when exposing or writing audit
def _mask_signal(sig: Any) -> Any:
    if not isinstance(sig, dict):
        return sig
    out = {}
    for k, v in sig.items():
        lk = k.lower()
        if any(x in lk for x in ('secret', 'token', 'password', 'key', 'app_secret')):
            out[k] = '***MASKED***'
        elif 'account' in lk or ('no' in lk and isinstance(v, (str, int))):
            s = str(v)
            if len(s) > 4:
                out[k] = s[:2] + '...' + s[-2:]
            else:
                out[k] = '***'
        else:
            out[k] = v
    return out


class ApprovalManager:
    def __init__(self):
        self._lock = threading.Lock()
        # pending: approval_id -> record
        self._pending: Dict[str, Dict] = {}
        self._handler: Optional[Callable[[dict], None]] = None
        # load existing pending approvals (last state win)
        try:
            if PENDING_FILE.exists():
                with open(PENDING_FILE, 'r', encoding='utf-8') as fh:
                    for line in fh:
                        try:
                            rec = json.loads(line)
                            aid = rec.get('approval_id') or rec.get('id')
                            if not aid:
                                continue
                            # prefer the latest record for this id
                            self._pending[aid] = rec
                        except Exception:
                            continue
        except Exception:
            # keep going even if load fails
            pass

    # ---- registration / callback ----
    def register_handler(self, fn: Callable[[dict], None]):
        """Register a callable invoked asynchronously with the approved record."""
        self._handler = fn

    # ---- core API ----
    def submit(self, payload: Dict) -> str:
        """Submit an approval request. Payload can be an 'order' or a 'signal' dict.
        Returns approval_id (string).
        """
        aid = str(uuid.uuid4())
        rec = {
            'approval_id': aid,
            'timestamp': int(time.time()),
            'order': payload,
            'status': 'pending',
            'operator': None,
            'note': None,
        }
        with self._lock:
            self._pending[aid] = rec
        # persist queue and pending file
        try:
            with open(QUEUE_FILE, 'a', encoding='utf-8') as fh:
                fh.write(json.dumps({'id': aid, 'signal': _mask_signal(payload), 'timestamp': rec['timestamp']}, ensure_ascii=False) + '\n')
        except Exception:
            pass
        try:
            with open(PENDING_FILE, 'a', encoding='utf-8') as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + '\n')
        except Exception:
            pass

        # webhook notification (masked)
        try:
            webhook = os.environ.get('APPROVAL_WEBHOOK_URL')
            if webhook:
                payload_masked = {k: ('***MASKED***' if any(x in k.lower() for x in ('secret','token','password','key')) else v) for k,v in (payload.items() if isinstance(payload, dict) else [])}
                payload_body = {'event': 'approval_requested', 'id': aid, 'signal': payload_masked, 'timestamp': rec['timestamp']}
                # fire-and-forget
                import threading, requests
                threading.Thread(target=lambda: requests.post(webhook, json=payload_body, timeout=5), daemon=True).start()
        except Exception:
            pass

        return aid

    def list_pending(self) -> List[Dict]:
        """Return list of pending records (shallow copies)."""
        with self._lock:
            return [dict(r) for r in self._pending.values() if r.get('status') == 'pending']

    def check_approval(self, approval_id: str) -> str:
        with self._lock:
            rec = self._pending.get(approval_id)
            if not rec:
                return 'unknown'
            return rec.get('status', 'pending')

    def approve(self, approval_id: str, approver: Optional[str] = None, approve: bool = True, operator: Optional[str] = None, note: Optional[str] = None) -> bool:
        """Approve or reject a pending request. Backwards-compatible signature:
        - realtime_trader style: approve(req_id, approver, approve=True)
        - GUI style: approve(req_id, operator=..., note=...)
        """
        with self._lock:
            rec = self._pending.get(approval_id)
            if not rec:
                return False
            rec['status'] = 'approved' if approve else 'rejected'
            # normalize actor fields
            if approver:
                rec['approved_by'] = approver
            if operator:
                rec['operator'] = operator
            if note:
                rec['note'] = note
            rec['approved_at'] = int(time.time())
        # append audit and pending update
        try:
            with open(AUDIT_FILE, 'a', encoding='utf-8') as fh:
                audit = {
                    'id': approval_id,
                    'signal': _mask_signal(rec.get('order')),
                    'approved': rec['status'] == 'approved',
                    'approver': approver or operator,
                    'ts': rec.get('approved_at')
                }
                fh.write(json.dumps(audit, ensure_ascii=False) + '\n')
        except Exception:
            pass
        try:
            with open(PENDING_FILE, 'a', encoding='utf-8') as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + '\n')
        except Exception:
            pass

        # call handler if approved
        if rec['status'] == 'approved' and self._handler:
            # For backward compatibility with callers that expect 'signal'
            # key (e.g., RealtimeTrader._on_approved_record), provide a copy
            # where 'signal' maps to the original payload if needed.
            arg = dict(rec)
            if 'signal' not in arg and 'order' in arg:
                arg['signal'] = arg.get('order')
            # prefer synchronous call to ensure handler runs in tests; fall back to thread
            try:
                self._handler(arg)
            except Exception:
                try:
                    threading.Thread(target=self._handler, args=(arg,), daemon=True).start()
                except Exception:
                    pass

        # webhook
        try:
            webhook = os.environ.get('APPROVAL_WEBHOOK_URL')
            if webhook:
                payload = {'event': 'approval_decision', 'id': approval_id, 'approved': rec['status'] == 'approved', 'approver': approver or operator, 'timestamp': rec.get('approved_at')}
                import threading, requests
                threading.Thread(target=lambda: requests.post(webhook, json=payload, timeout=5), daemon=True).start()
        except Exception:
            pass

        # remove from pending
        with self._lock:
            self._pending.pop(approval_id, None)

        return True

    def reject(self, approval_id: str, operator: Optional[str] = None, note: Optional[str] = None) -> bool:
        # convenience wrapper
        return self.approve(approval_id, operator=operator, approve=False, note=note)


# module-level singleton
manager = ApprovalManager()
