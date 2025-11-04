Deployment notes
=================

This project includes a small FastAPI webhook listener and can be deployed with Docker.

Quick start (local, requires Docker):

1. Build and run with docker-compose

```bash
docker-compose up --build
```

2. The webhook will listen on http://localhost:8000/webhook/order

3. Configure a secret for signature verification:

```bash
export BROKER_WEBHOOK_SECRET="your-secret"
```

4. For production use, place the app behind TLS (nginx or cloud load balancer) and enable the secret.

Systemd service example (on a Linux host running the container):

```ini
[Unit]
Description=Trading Bot Webhook
After=docker.service

[Service]
Restart=always
WorkingDirectory=/srv/trading-bot
ExecStart=/usr/bin/docker-compose up
ExecStop=/usr/bin/docker-compose down

[Install]
WantedBy=multi-user.target
```

Security notes
--------------
- Always enable `BROKER_WEBHOOK_SECRET` and verify signatures.
- Use HTTPS/TLS between broker and your webhook endpoint.
- Do not expose the webhook port publicly without protection (WAF, IP allowlist).

