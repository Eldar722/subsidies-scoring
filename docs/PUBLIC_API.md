# 📊 Public API — Share Data Without Exposing Secrets

**No authentication required.** Anyone can access read-only data via public API endpoints.

## The Problem

When you clone and run the project locally, you need Supabase credentials (`.env` file). But sharing credentials is risky and allows full database access.

## The Solution

Use **Public API endpoints** to share data without credentials:

```bash
# Health check
curl http://localhost:8000/public/health

# Get producers
curl http://localhost:8000/public/producers?limit=100

# Get ML scores
curl http://localhost:8000/public/scores?limit=100

# Get combined data (producers + scores)
curl http://localhost:8000/public/data?limit=50

# Get model metrics
curl http://localhost:8000/public/metrics

# Get statistics
curl http://localhost:8000/public/stats
```

---

## API Endpoints

### `/public/health`
**GET** — Health check

Check if backend is running.

```bash
curl http://localhost:8000/public/health
```

Response:
```json
{
  "status": "ok",
  "message": "Backend is running"
}
```

---

### `/public/producers`
**GET** — List of producers (read-only)

**Parameters:**
- `limit` (optional): Maximum number of producers to return (default: 100)

```bash
curl "http://localhost:8000/public/producers?limit=50"
```

Response:
```json
{
  "count": 50,
  "data": [
    {
      "producer_id": "PROD_001",
      "region": "Актюбинская область",
      "direction": "Животноводство",
      "total_applications": 5,
      "completion_rate": 0.92
    },
    ...
  ],
  "limit": 50
}
```

---

### `/public/scores`
**GET** — ML scores and rankings (read-only)

**Parameters:**
- `limit` (optional): Maximum number of scores to return (default: 100)

```bash
curl "http://localhost:8000/public/scores?limit=50"
```

Response:
```json
{
  "count": 50,
  "data": [
    {
      "producer_id": "PROD_001",
      "ml_score": 0.87,
      "ml_rank": 12,
      "fcfs_rank": 45,
      "delta": -33,
      "hidden_talent": false
    },
    ...
  ],
  "limit": 50
}
```

**Key fields:**
- `ml_score`: AI score (0-1)
- `ml_rank`: AI ranking position
- `fcfs_rank`: First-come-first-served ranking
- `delta`: Difference (ml_rank - fcfs_rank)
- `hidden_talent`: True if producer ranked higher by AI

---

### `/public/data`
**GET** — Combined producers + scores (read-only)

**Parameters:**
- `limit` (optional): Maximum number of records to return (default: 50)

```bash
curl "http://localhost:8000/public/data?limit=30"
```

Response:
```json
{
  "count": 30,
  "data": [
    {
      "producer_id": "PROD_001",
      "ml_score": 0.87,
      "ml_rank": 12,
      "fcfs_rank": 45,
      "delta": -33,
      "hidden_talent": false,
      "region": "Актюбинская область",
      "direction": "Животноводство",
      "total_applications": 5,
      "completion_rate": 0.92
    },
    ...
  ],
  "limit": 30
}
```

---

### `/public/metrics`
**GET** — Model metrics and performance

```bash
curl http://localhost:8000/public/metrics
```

Response:
```json
{
  "status": "ok",
  "metrics": {
    "model_accuracy": 0.89,
    "model_precision": 0.85,
    "model_recall": 0.82,
    "fairness_score": 0.91,
    "last_trained": "2026-04-03T15:45:00Z"
  }
}
```

---

### `/public/stats`
**GET** — Summary statistics

```bash
curl http://localhost:8000/public/stats
```

Response:
```json
{
  "total_producers": 2847,
  "total_scores": 2847,
  "regions": {
    "Актюбинская область": 340,
    "Жамбылская область": 285,
    "Карагандинская область": 412,
    ...
  },
  "top_regions": [
    ["Карагандинская область", 412],
    ["Актюбинская область", 340],
    ["Жамбылская область", 285],
    ...
  ]
}
```

---

## 🔐 Security

✅ **Read-only** — No write/delete operations  
✅ **No authentication** — Anyone can access  
✅ **No secrets exposed** — Only aggregated, public data  
✅ **Rate limited** — 100 requests per minute per IP  
✅ **CORS enabled** — Can be accessed from browsers  

**What you CAN'T access:**
- ❌ Supabase credentials
- ❌ API keys
- ❌ Private data
- ❌ Write/delete operations
- ❌ Admin functions

---

## 📋 Sharing Instructions

### For Collaborators

1. **Clone the project** (no credentials needed)
   ```bash
   git clone https://github.com/Eldar722/subsidies-scoring.git
   cd subsidies-scoring
   ```

2. **Run backend** (with YOUR Supabase credentials in `.env`)
   ```bash
   cd backend
   # Create .env with SUPABASE_URL and SUPABASE_ANON_KEY
   python main.py
   ```

3. **Run frontend** (connects to `localhost:8000`)
   ```bash
   cd ../frontend
   npm run dev
   ```

4. **Access public API** (no credentials needed)
   ```bash
   curl http://localhost:8000/public/data?limit=50
   ```

---

## 💡 Use Cases

| Use Case | Method |
|----------|--------|
| **Review data before setting up** | Use public API |
| **Explore without credentials** | Use public API |
| **Integrate into another app** | Use public API |
| **Full access + write operations** | Use admin API with credentials in `.env` |

---

## 🚀 Deploy Public API

You can deploy the backend anywhere and share the public URL:

```bash
# Deployed backend
https://subsidy-api.example.com/public/data?limit=50

# Collaborators can access without credentials
curl https://subsidy-api.example.com/public/data
```

**Everyone can access public endpoints—no credentials needed.**

---

## ⚠️ What About Private Data?

All other API endpoints (admin, analytics, fairness, etc.) **require authentication** via Supabase credentials in `.env`.

Only the `/public/*` endpoints are accessible without credentials.

---

## 📊 Example: Embed Data in Another App

```html
<!-- Get data from public API -->
<script>
  fetch('http://localhost:8000/public/stats')
    .then(r => r.json())
    .then(data => {
      document.getElementById('total').textContent = data.total_producers;
      document.getElementById('regions').textContent = data.top_regions.length;
    });
</script>

<div>
  Total Producers: <span id="total">—</span>
  Regions: <span id="regions">—</span>
</div>
```

---

**✅ Setup complete.** Share the public API URL with collaborators instead of credentials!
