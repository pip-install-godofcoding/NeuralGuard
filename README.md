# NeuralGuard MVP

> Transparent LLM proxy with semantic caching, smart routing, and trust scoring.

---

## Architecture

```
Your App
  │ base_url = "http://localhost:8000/v1"
  │ api_key  = "ng-..."
  ▼
┌─────────────────────────────┐
│    FastAPI Proxy (Port 8000) │
│                             │
│ 1. Auth validation          │
│ 2. Semantic cache check     │  ──► Redis Stack
│ 3. Heuristic model routing  │
│ 4. Forward to OpenAI        │  ──► api.openai.com
│ 5. Store in cache           │
│ 6. Log query                │  ──► Supabase PostgreSQL
│ 7. Trust scoring (async)    │  ──► gpt-4o-mini
└─────────────────────────────┘
  │
  ▼
┌────────────────────────┐
│ Next.js Dashboard      │
│ (Port 3000)            │
│ - Overview stats       │
│ - Cost saved charts    │
│ - Query log table      │
│ - API key management   │
└────────────────────────┘
```

---

## Quick Start

### Prerequisites
- Docker (for Redis Stack)
- Python 3.12+
- Node.js 18+
- A Supabase project (free tier is fine)
- An OpenAI API key

---

### Step 1 — Supabase Setup

1. Go to [supabase.com](https://supabase.com) and create a new project.
2. In the SQL Editor, run the contents of `proxy/db/schema.sql`.
3. Copy your **Project URL** and **service_role** key (not anon key).

---

### Step 2 — Proxy Setup

```bash
cd proxy

# Copy and fill in your secrets
cp .env.example .env

# Install dependencies
pip install -r requirements.txt

# Start Redis Stack locally
docker run -d --name redis-stack -p 6379:6379 redis/redis-stack:latest

# Start the proxy
uvicorn main:app --reload --port 8000
```

Verify: `curl http://localhost:8000/health`

---

### Step 3 — Create Your First NeuralGuard API Key

```bash
# Set ADMIN_SECRET in your .env first, then:
curl -X POST http://localhost:8000/admin/create-key \
  -H "Content-Type: application/json" \
  -H "X-Admin-Secret: YOUR_ADMIN_SECRET" \
  -d '{"user_id": "YOUR_SUPABASE_USER_UUID", "label": "Dev Key"}'
```

You'll get back `{"key": "ng-...", "message": "Copy this key..."}`.

---

### Step 4 — Test the Proxy

```python
from openai import OpenAI

client = OpenAI(
    api_key="ng-YOUR_NEURALGUARD_KEY",     # ← NeuralGuard key
    base_url="http://localhost:8000/v1",   # ← NeuralGuard proxy
)

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Translate 'hello' to Spanish"}]
)
print(response.choices[0].message.content)
# Note: "translate" heuristic routes this to gpt-4o-mini automatically!
```

Run the same query twice — the second call hits the semantic cache.

---

### Step 5 — Dashboard Setup

```bash
cd dashboard

# Copy and fill in dashboard secrets
cp .env.local.example .env.local

npm install
npm run dev
# Open http://localhost:3000
```

Sign up with your email, log in, and see your cost savings.

---

## Key Features

| Feature | Details |
|---|---|
| **Transparent Proxy** | Drop-in OpenAI `base_url` replacement |
| **Semantic Cache** | Cosine similarity ≥ 0.95 → $0 API call, <100ms response |
| **Smart Routing** | 15+ heuristic patterns silently downgrade expensive models |
| **Trust Engine** | Async gpt-4o-mini scores response factuality 0–100 |
| **Fail-Open** | Cache/Router/Trust failures never block requests |
| **Dashboard** | Real-time cost saved, query logs, API key management |

---

## Model Routing Rules

Requests to `gpt-4o` with simple prompts are silently routed to `gpt-4o-mini`:

- Translation ("translate to...")
- Summarization ("summarize...", "in one sentence")
- Grammar fixes ("fix grammar", "correct spelling")
- Simple Q&A ("what is X?", "define X")
- Short prompts (≤ 60 words)
- Format conversions, list generation, paraphrasing

---

## Environment Variables

### Proxy (`proxy/.env`)

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | Your real OpenAI key (never exposed to clients) |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Supabase service role key |
| `REDIS_URL` | Redis connection string (default: `redis://localhost:6379`) |
| `ADMIN_SECRET` | Secret for `/admin/create-key` endpoint |

### Dashboard (`dashboard/.env.local`)

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Same Supabase URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon key |
| `SUPABASE_SERVICE_KEY` | Service key (for key creation API route) |
| `NEXT_PUBLIC_PROXY_URL` | Proxy base URL (shown to users) |

---

## Production Deployment

- **Proxy**: Deploy to [Render](https://render.com) or [Fly.io](https://fly.io) as a Docker container.
- **Redis**: Use [Upstash Redis](https://upstash.com) (free tier, no RediSearch needed).
- **Dashboard**: Deploy to [Vercel](https://vercel.com) — connect to your GitHub repo.
- **Database**: Already managed by Supabase.
