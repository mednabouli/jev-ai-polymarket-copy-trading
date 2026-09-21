# Jev AI Helm Chart

Deploys the Jev AI orchestrator and its MCP services.

## Install

Create a Kubernetes Secret rather than passing credentials through Helm CLI history:

```bash
kubectl create namespace jev-ai
kubectl -n jev-ai create secret generic jev-ai-secrets \
  --from-literal=CLAUDE_CODE_OAUTH_TOKEN='...' \
  --from-literal=TELEGRAM_BOT_TOKEN='...' \
  --from-literal=TELEGRAM_CHAT_ID='...' \
  --from-literal=POSTGRES_PASSWORD='...'

helm upgrade --install jev-ai ./charts/jev-ai -n jev-ai \
  --set jevAi.secrets.existingSecret=jev-ai-secrets
```

## Validate

```bash
helm lint ./charts/jev-ai
kubectl -n jev-ai get pods,svc
```

Use immutable image tags and a managed PostgreSQL service in production. The current project uses simulated order execution; do not attach a funded wallet until the execution layer has been implemented, audited, and tested.
