# Vercel Commands - AI-RFX Backend

## Comandos Base

```bash
# Sincronizar variables desde .env -> Vercel (una sola vez o cuando cambien)
./scripts/vercel_sync_env.sh .env production,preview

# Deploy preview
./scripts/vercel_deploy.sh preview

# Deploy production
./scripts/vercel_deploy.sh production
```

## Deploy Manual con CLI

```bash
# Preview
vercel deploy --yes

# Production
vercel deploy --prod --yes
```

## Verificar Proyecto Vinculado

```bash
cat .vercel/project.json
vercel whoami
```

## Health Checks

```bash
curl https://<backend-vercel-url>/health
curl https://<backend-vercel-url>/api/health
```
