"""FastAPI webhook listener for broker order events with optional HMAC verification.

This provides a production-ready ASGI app to receive broker webhooks. It
verifies signatures when BROKER_WEBHOOK_SECRET is set, persists events via
OrderManager, and exposes a simple health endpoint.

Run with:
  pip install fastapi uvicorn
  uvicorn src.trading.webhook_api:app --host 0.0.0.0 --port 8000

Note: Do NOT expose without TLS and request signing in production.
"""
import os
import hmac
import hashlib
from typing import Optional
from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import JSONResponse

from src.trading.order_manager import OrderManager

app = FastAPI(title="Trading Bot Webhook API")

ORDER_LOG = os.environ.get('ORDER_LOG_PATH', os.path.join('results', 'order_log.jsonl'))
WEBHOOK_SECRET = os.environ.get('BROKER_WEBHOOK_SECRET')
om = OrderManager(log_path=ORDER_LOG)


def verify_signature(body: bytes, signature: str, secret: str) -> bool:
    """Verify HMAC-SHA256 signature header. signature is hex or prefix like 'sha256=...'."""
    if signature.startswith('sha256='):
        signature = signature.split('=', 1)[1]
    mac = hmac.new(secret.encode('utf-8'), msg=body, digestmod=hashlib.sha256)
    return hmac.compare_digest(mac.hexdigest(), signature)


@app.get('/health')
async def health():
    return {'status': 'ok'}


@app.post('/webhook/order')
async def order_webhook(request: Request, x_signature: Optional[str] = Header(None)):
    raw = await request.body()

    if WEBHOOK_SECRET:
        if not x_signature:
            raise HTTPException(status_code=401, detail='Missing signature header')
        if not verify_signature(raw, x_signature, WEBHOOK_SECRET):
            raise HTTPException(status_code=401, detail='Invalid signature')

    payload = None
    try:
        payload = await request.json()
    except Exception:
        # fallback: treat body as raw text
        payload = {'raw': raw.decode('utf-8', errors='ignore')}

    # try to extract order id
    order_id = None
    if isinstance(payload, dict):
        order_id = payload.get('order_id') or payload.get('orderNo') or (payload.get('output') or {}).get('orderId')

    rec = {
        'event': 'webhook.order',
        'order_id': order_id,
        'payload': payload
    }
    om._persist(rec)

    return JSONResponse({'status': 'accepted', 'order_id': order_id})


def run_app():
    import uvicorn
    port = int(os.environ.get('WEBHOOK_PORT', 8000))
    uvicorn.run('src.trading.webhook_api:app', host='0.0.0.0', port=port, log_level='info')


if __name__ == '__main__':
    run_app()
