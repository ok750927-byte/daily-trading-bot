"""Minimal webhook listener skeleton for broker events.

This file provides a tiny Flask app that can accept POSTed order events
from a broker (if the broker supports webhooks). It's intentionally small
so it can be expanded to handle authentication/signature verification and
to integrate with OrderManager in a production deployment.

Use this only as a starting point; do NOT expose to the public internet
without TLS and signature verification.
"""
from flask import Flask, request, jsonify
import os
import json
from src.trading.order_manager import OrderManager

app = Flask(__name__)

# order log path can be configured via env
ORDER_LOG = os.environ.get('ORDER_LOG_PATH', os.path.join('results', 'order_log.jsonl'))
om = OrderManager(log_path=ORDER_LOG)


@app.route('/webhook/order', methods=['POST'])
def order_webhook():
    """Receive order events from broker and persist them.

    Expected JSON payload depends on the broker. This endpoint will
    store the raw payload and attempt to extract an order_id if present.
    """
    payload = request.get_json(force=True, silent=True)
    if payload is None:
        return jsonify({'error': 'invalid json'}), 400

    # attempt to extract an id
    order_id = None
    if isinstance(payload, dict):
        order_id = payload.get('order_id') or payload.get('orderNo') or (payload.get('output') or {}).get('orderId')

    rec = {
        'event': 'webhook_received',
        'order_id': order_id,
        'payload': payload
    }
    om._persist(rec)

    return jsonify({'status': 'ok', 'order_id': order_id}), 200


def run_app(port=5000):
    # WARNING: For local development only, do not use Flask's dev server in production.
    app.run(host='0.0.0.0', port=int(port), debug=False)


if __name__ == '__main__':
    run_app()
