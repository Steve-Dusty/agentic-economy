# Public External Access Setup for Trinity

> **Purpose**: Enable external (non-VPN) access to Trinity's public agent chat links while keeping the main platform internal.
> **Infrastructure**: GCP + Tailscale VPN
> **Status**: Implemented (Option 2 - GCP Load Balancer)
> **Date**: 2026-02-17

---

## Current State

- Trinity runs on GCP VM (`ability-services` in `us-central1-a`)
- Platform accessible via Tailscale VPN at `https://trinity.abilityai.dev`
- **External public access** available at `https://public.abilityai.dev`
- Cloud Armor security policy restricts external access to public routes only

## Architecture

```
                                    ┌─────────────────────────────────────┐
                                    │         ability-services VM         │
                                    │         (10.128.0.5 internal)       │
                                    │         (34.121.25.80 external)     │
┌──────────────┐                    │                                     │
│ VPN Users    │ ──► Tailscale ──► │ Caddy (:443) ──► Frontend (:80)    │
│              │     (internal)     │       └──────► Backend (:8000)     │
└──────────────┘                    │                                     │
                                    │                                     │
┌──────────────┐    ┌───────────┐   │                                     │
│ Public Users │ ──►│ GCP LB    │──►│ Frontend (:80) ──► Backend (:8000) │
│              │    │ + Cloud   │   │ (nginx proxy)                       │
└──────────────┘    │ Armor     │   │                                     │
                    │ (filtered)│   └─────────────────────────────────────┘
                    └───────────┘
                    34.160.193.214
                    public.abilityai.dev
```

---

## Endpoints Exposed Externally

Only these routes are allowed through Cloud Armor:

| Route | Type | Purpose |
|-------|------|---------|
| `/` | Frontend | Root (loads SPA) |
| `/chat/*` | Frontend | Public chat UI |
| `/api/public/*` | Backend | Public API endpoints |
| `/assets/*` | Frontend | Static assets (JS, CSS) |
| `/vite.svg`, `/favicon.ico` | Frontend | Icons |

Everything else returns **403 Forbidden**.

---

## Option 1: Tailscale Funnel

> **Note**: Tailscale Funnel conflicts with Caddy when both try to serve HTTPS on port 443 via the Tailscale interface. If you use Caddy for internal HTTPS (like `trinity.abilityai.dev`), Funnel will break internal access.

### When to Use
- No existing HTTPS reverse proxy on the server
- Quick setup needed
- Don't need custom domain

### Conflict Warning
If Caddy handles internal HTTPS on port 443, enabling Tailscale Funnel will intercept all HTTPS traffic on the Tailscale interface, breaking internal access. Choose one:
- **Funnel only**: Use `https://<machine>.ts.net` for both internal and external
- **Caddy only**: Use GCP LB or Cloudflare Tunnel for external access

---

## Option 2: GCP Load Balancer + Cloud Armor (Implemented)

This is the **production setup** for `ability-services`.

### Pros
- Custom domain (`public.abilityai.dev`)
- Cloud Armor path-based filtering (only public routes exposed)
- Google-managed SSL certificate
- No conflict with Tailscale/Caddy internal access
- DDoS protection included

### Cons
- Monthly cost (~$18/month)
- More complex setup
- Requires VM to have external IP for health checks

### Resources Created

| Resource | Name | Purpose |
|----------|------|---------|
| Static IP | `trinity-public-ip` | 34.160.193.214 |
| Instance Group | `trinity-ig` | Contains ability-services VM |
| Health Check | `trinity-health-check` | HTTP check on port 80 |
| Backend Service | `trinity-backend-service` | Routes to instance group |
| URL Map | `trinity-url-map` | Routes all traffic to backend |
| SSL Certificate | `trinity-public-cert` | Google-managed for public.abilityai.dev |
| HTTPS Proxy | `trinity-https-proxy` | Terminates SSL |
| HTTP Proxy | `trinity-http-proxy` | For HTTP access |
| Forwarding Rules | `trinity-https-forwarding`, `trinity-http-forwarding` | Connect IP to proxies |
| Security Policy | `trinity-public-policy` | Cloud Armor path filtering |
| Firewall Rule | `allow-trinity-web` | Allow ports 80, 443 to VM |
| DNS Record | `public.abilityai.dev` | A record → 34.160.193.214 |

### Complete Setup Commands

```bash
PROJECT=mcp-server-project-455215
ZONE=us-central1-a
VM_NAME=ability-services

# 1. Reserve static external IP
gcloud compute addresses create trinity-public-ip --global --project=$PROJECT

# Get the IP address
gcloud compute addresses describe trinity-public-ip --global --project=$PROJECT --format='value(address)'
# Result: 34.160.193.214

# 2. Ensure VM has external IP (required for health checks)
gcloud compute instances add-access-config $VM_NAME --zone=$ZONE --project=$PROJECT

# 3. Create firewall rule for VM
gcloud compute firewall-rules create allow-trinity-web \
  --allow=tcp:80,tcp:443 \
  --source-ranges=0.0.0.0/0 \
  --target-tags=ability-services \
  --project=$PROJECT

# 4. Create instance group and add VM
gcloud compute instance-groups unmanaged create trinity-ig \
  --zone=$ZONE --project=$PROJECT

gcloud compute instance-groups unmanaged add-instances trinity-ig \
  --zone=$ZONE --instances=$VM_NAME --project=$PROJECT

gcloud compute instance-groups unmanaged set-named-ports trinity-ig \
  --zone=$ZONE --named-ports=http:80 --project=$PROJECT

# 5. Create health check
gcloud compute health-checks create http trinity-health-check \
  --port=80 --request-path=/ --project=$PROJECT

# 6. Create backend service
gcloud compute backend-services create trinity-backend-service \
  --protocol=HTTP --port-name=http \
  --health-checks=trinity-health-check \
  --global --project=$PROJECT

gcloud compute backend-services add-backend trinity-backend-service \
  --instance-group=trinity-ig \
  --instance-group-zone=$ZONE \
  --global --project=$PROJECT

# 7. Create URL map
gcloud compute url-maps create trinity-url-map \
  --default-service=trinity-backend-service \
  --global --project=$PROJECT

# 8. Create SSL certificate (Google-managed)
gcloud compute ssl-certificates create trinity-public-cert \
  --domains=public.abilityai.dev \
  --global --project=$PROJECT

# 9. Create HTTPS proxy and forwarding rule
gcloud compute target-https-proxies create trinity-https-proxy \
  --url-map=trinity-url-map \
  --ssl-certificates=trinity-public-cert \
  --global --project=$PROJECT

gcloud compute forwarding-rules create trinity-https-forwarding \
  --address=trinity-public-ip \
  --target-https-proxy=trinity-https-proxy \
  --ports=443 \
  --global --project=$PROJECT

# 10. Create HTTP proxy and forwarding rule (optional, for redirect)
gcloud compute target-http-proxies create trinity-http-proxy \
  --url-map=trinity-url-map \
  --global --project=$PROJECT

gcloud compute forwarding-rules create trinity-http-forwarding \
  --address=trinity-public-ip \
  --target-http-proxy=trinity-http-proxy \
  --ports=80 \
  --global --project=$PROJECT

# 11. Add DNS record
gcloud dns record-sets create public.abilityai.dev \
  --zone=abilityai-dev-zone \
  --type=A --ttl=300 \
  --rrdatas=34.160.193.214 \
  --project=$PROJECT

# 12. Wait for SSL certificate (can take up to 60 minutes)
watch -n 30 "gcloud compute ssl-certificates describe trinity-public-cert \
  --global --project=$PROJECT --format='value(managed.status)'"
# Wait until status shows: ACTIVE
```

### Cloud Armor Security Policy

This is **critical** - without this, the entire platform is exposed publicly.

```bash
PROJECT=mcp-server-project-455215

# 1. Create security policy
gcloud compute security-policies create trinity-public-policy \
  --description="Only allow public chat routes" \
  --project=$PROJECT

# 2. Add allow rules for public routes
gcloud compute security-policies rules create 1000 \
  --security-policy=trinity-public-policy \
  --action=allow \
  --expression="request.path.matches('/chat/.*')" \
  --description="Allow public chat pages" \
  --project=$PROJECT

gcloud compute security-policies rules create 1001 \
  --security-policy=trinity-public-policy \
  --action=allow \
  --expression="request.path.matches('/api/public/.*')" \
  --description="Allow public API endpoints" \
  --project=$PROJECT

gcloud compute security-policies rules create 1002 \
  --security-policy=trinity-public-policy \
  --action=allow \
  --expression="request.path.matches('/assets/.*')" \
  --description="Allow frontend assets" \
  --project=$PROJECT

gcloud compute security-policies rules create 1003 \
  --security-policy=trinity-public-policy \
  --action=allow \
  --expression="request.path == '/' || request.path == '/vite.svg' || request.path == '/favicon.ico'" \
  --description="Allow root and static files" \
  --project=$PROJECT

# 3. Set default rule to deny
gcloud compute security-policies rules update 2147483647 \
  --security-policy=trinity-public-policy \
  --action=deny-403 \
  --project=$PROJECT

# 4. Attach policy to backend service
gcloud compute backend-services update trinity-backend-service \
  --security-policy=trinity-public-policy \
  --global --project=$PROJECT
```

### Verify Security Policy

```bash
# Should return 200:
curl -s -o /dev/null -w "%{http_code}" "https://public.abilityai.dev/"
curl -s -o /dev/null -w "%{http_code}" "https://public.abilityai.dev/chat/test-token"
curl -s -o /dev/null -w "%{http_code}" "https://public.abilityai.dev/api/public/link/test"

# Should return 403:
curl -s -o /dev/null -w "%{http_code}" "https://public.abilityai.dev/api/agents"
curl -s -o /dev/null -w "%{http_code}" "https://public.abilityai.dev/login"
curl -s -o /dev/null -w "%{http_code}" "https://public.abilityai.dev/api/auth/mode"
```

---

## Option 3: Cloudflare Tunnel

Alternative if you don't want GCP LB costs or complexity.

### Pros
- Free tier available
- Built-in path filtering in config
- No firewall changes needed
- DDoS protection included

### Setup Steps

1. **Install cloudflared on VM**
   ```bash
   wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
   sudo dpkg -i cloudflared-linux-amd64.deb
   ```

2. **Login and create tunnel**
   ```bash
   cloudflared tunnel login
   cloudflared tunnel create trinity-public
   ```

3. **Configure tunnel** (`~/.cloudflared/config.yml`)
   ```yaml
   tunnel: trinity-public
   credentials-file: /root/.cloudflared/<tunnel-id>.json

   ingress:
     - hostname: public.abilityai.dev
       path: /chat/*
       service: http://localhost:80
     - hostname: public.abilityai.dev
       path: /api/public/*
       service: http://localhost:80
     - hostname: public.abilityai.dev
       path: /assets/*
       service: http://localhost:80
     - hostname: public.abilityai.dev
       path: /
       service: http://localhost:80
     - service: http_status:403
   ```

4. **Run as service**
   ```bash
   sudo cloudflared service install
   sudo systemctl enable cloudflared
   sudo systemctl start cloudflared
   ```

5. **Add DNS record in Cloudflare**
   - CNAME `public` -> `<tunnel-id>.cfargotunnel.com`

---

## Trinity Configuration

### Environment Variable

Add to `~/trinity/.env` on the server:
```bash
# External URL for public chat links
PUBLIC_CHAT_URL=https://public.abilityai.dev
```

### Restart Backend

```bash
cd ~/trinity
sudo docker compose -f docker-compose.prod.yml up -d backend
```

### Verify Configuration

```bash
sudo docker exec trinity-backend python -c "from config import PUBLIC_CHAT_URL; print('PUBLIC_CHAT_URL:', PUBLIC_CHAT_URL)"
# Should show: PUBLIC_CHAT_URL: https://public.abilityai.dev
```

---

## Code Changes (Already Implemented)

The following code changes were made to support external URLs:

### Backend

**`src/backend/config.py`**
```python
PUBLIC_CHAT_URL = os.getenv("PUBLIC_CHAT_URL", "")

# Auto-add to CORS if set
if PUBLIC_CHAT_URL:
    _extra_origins.append(PUBLIC_CHAT_URL)
```

**`src/backend/db_models.py`**
```python
class PublicLinkWithUrl(PublicLink):
    url: str  # Internal URL
    external_url: Optional[str] = None  # External URL (if configured)
```

**`src/backend/routers/public_links.py`**
```python
def _build_external_url(token: str) -> str | None:
    if PUBLIC_CHAT_URL:
        return f"{PUBLIC_CHAT_URL}/chat/{token}"
    return None
```

**`docker-compose.prod.yml`**
```yaml
environment:
  - PUBLIC_CHAT_URL=${PUBLIC_CHAT_URL:-}
```

### Frontend

**`src/frontend/src/components/PublicLinksPanel.vue`**
- Shows external URL in link preview when available
- "Copy Internal Link" button (clipboard icon)
- "Copy External Link" button (globe icon) - only shown when external_url exists

---

## Security Summary

| Layer | Protection |
|-------|------------|
| **Cloud Armor** | Path-based filtering (403 for non-public routes) |
| **Token Security** | 192-bit random strings (unguessable) |
| **Rate Limiting** | 30 requests/min per IP (backend) |
| **Email Verification** | Optional per-link |
| **Link Expiration** | Optional per-link |
| **Audit Logging** | All public access logged |

---

## Testing Checklist

- [x] `https://public.abilityai.dev/chat/<token>` accessible from outside VPN
- [x] `https://public.abilityai.dev/api/public/link/<token>` returns link info
- [x] `https://public.abilityai.dev/api/agents` returns 403
- [x] `https://public.abilityai.dev/login` returns 403
- [x] `https://trinity.abilityai.dev/` still works for VPN users
- [ ] Public chat works end-to-end with real agent
- [ ] Email verification works (if enabled)
- [ ] Rate limiting works (31+ requests in a minute)

---

## Troubleshooting

### SSL Certificate Stuck in PROVISIONING

```bash
# Check status
gcloud compute ssl-certificates describe trinity-public-cert \
  --global --project=$PROJECT --format='yaml(managed)'

# Verify DNS points to LB IP
dig +short public.abilityai.dev
# Should return: 34.160.193.214
```

Certificate provisioning requires DNS to be correctly configured. Can take up to 60 minutes.

### Backend Shows UNHEALTHY

```bash
# Check health
gcloud compute backend-services get-health trinity-backend-service \
  --global --project=$PROJECT

# Verify VM has external IP
gcloud compute instances describe ability-services \
  --zone=us-central1-a --project=$PROJECT \
  --format='value(networkInterfaces[0].accessConfigs[0].natIP)'

# Verify firewall rule
gcloud compute firewall-rules describe allow-trinity-web --project=$PROJECT
```

### Security Policy Not Working

```bash
# Verify policy is attached
gcloud compute backend-services describe trinity-backend-service \
  --global --project=$PROJECT --format='value(securityPolicy)'

# Re-attach if needed
gcloud compute backend-services update trinity-backend-service \
  --security-policy=trinity-public-policy \
  --global --project=$PROJECT

# Wait 30-60 seconds for propagation
```

---

## Cost Estimate

| Resource | Monthly Cost |
|----------|--------------|
| Global forwarding rule | ~$18 |
| Backend service | Included |
| Cloud Armor | Free (basic) |
| Static IP | ~$7 (if unused) |
| **Total** | ~$18-25/month |

---

## Files Referenced

- `src/backend/config.py` - PUBLIC_CHAT_URL config
- `src/backend/db_models.py` - PublicLinkWithUrl model
- `src/backend/routers/public_links.py` - External URL generation
- `src/frontend/src/components/PublicLinksPanel.vue` - Copy External Link button
- `docker-compose.prod.yml` - Environment variable exposure

---

*Last updated: 2026-02-17*
