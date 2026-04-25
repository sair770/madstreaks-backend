# Backend Architecture & API Reference

**Framework:** FastAPI (Python 3.11+)  
**Database:** Supabase (PostgreSQL)  
**Async Runtime:** asyncio + uvicorn  
**Deploy:** Railway.app

---

## Project Structure

```
app/
├── main.py              # FastAPI app, endpoints, lifespan
├── config.py            # Settings from .env
├── schemas.py           # Pydantic validation models
├── database.py          # Supabase client
├── auth.py              # JWT token validation
│
├── groww/               # Groww integration
│   ├── client.py        # API client + access token
│   ├── feed.py          # Live price WebSocket
│   └── orders.py        # Place/track orders
│
├── telegram/            # Telegram bot
│   ├── bot.py           # Bot setup + polling
│   └── handlers.py      # Command handlers
│
├── watchlist/           # Alert management
│   ├── manager.py       # Load + check conditions
│   └── notifier.py      # Send alerts
│
└── signals/             # Trade signals
    └── generator.py     # Format + post to channel
```

---

## Core Modules

### 1. Authentication (`app/auth.py`)

**Function:** `verify_user_token(authorization: str = Header(None)) -> str`

**Flow:**
```
1. Receive: Authorization: Bearer eyJhbGc...
2. Extract: token = "eyJhbGc..."
3. Decode: 
   - Split by "." → [header, payload, signature]
   - Base64 decode payload
   - JSON parse → {"sub": "user-uuid", "exp": 1234567, ...}
4. Validate:
   - Check "sub" (user_id) exists
   - Check expiry (exp > current_time)
5. Return: user_id (UUID)
```

**Error Handling:**
- Missing header → 401 "Missing Authorization header"
- Invalid format → 401 "Invalid Authorization format. Use: Bearer <token>"
- Invalid token → 401 "Invalid token: ..."
- Token expired → 401 "Token expired"

**Used By:** All protected endpoints (trades, alerts, signals)

---

### 2. Database (`app/database.py`)

**Supabase Python Client**
```python
from supabase import create_client

db.client = create_client(
  SUPABASE_URL,
  SUPABASE_SERVICE_KEY  # ← Has admin privileges, bypasses RLS
)
```

**Key Methods:**
- `db.client.table("trades").insert(data).execute()`
- `db.client.table("trades").select("*").eq("user_id", user_id).execute()`
- `db.client.table("trades").update(data).eq("id", id).eq("user_id", user_id).execute()`

**RLS (Row Level Security):**
Backend uses SERVICE_KEY which bypasses RLS. RLS policies protect against direct frontend access.

---

## API Endpoints

### Health & Debug

#### GET /health
Returns server + feed + database status
```json
{
  "status": "ok",
  "feed_running": true,
  "active_alerts": 5,
  "triggered_alerts": 2
}
```

#### GET /auth/debug
Debug endpoint for JWT decoding
```json
{
  "status": "ok",
  "message": "POST a JSON with 'token' field to test JWT decoding"
}
```

#### POST /auth/debug
Test JWT token decoding (for debugging only)
```
Request: {"token": "eyJhbGc..."}
Response: {
  "status": "✅ Decoded successfully",
  "user_id": "6db8e0db-d2b6-4827-ada9-570582b45aa1",
  "email": "user@example.com",
  "exp": 1777146674,
  "all_claims": [...]
}
```

---

### Trades

#### POST /trades
Create a new trade
```
Authorization: Bearer <jwt_token>
Content-Type: application/json

Body: {
  symbol: "NIFTY",
  entry_price: 23000,
  target_price: 23500,
  stop_loss: 22500,
  quantity: 1,
  trade_type: "long",  // or "short"
  status: "pending",   // or "open", "closed"
  notes: "..."
}

Validation (Pydantic):
- symbol: 1-20 chars
- entry_price: > 0
- quantity: > 0
- trade_type: matches pattern ^(long|short)$
- status: matches pattern ^(pending|open|closed)$

Response: 
{ "status": "created" }

Errors:
401 - Missing Authorization header
422 - Validation error (invalid fields)
500 - Database error
```

**⚠️ SCHEMA MISMATCH:** Backend schema only accepts 8 fields, Supabase table has 40+ fields.

#### GET /trades
List all trades (with optional user_id filter)
```
Authorization: Bearer <jwt_token>

Query params: ?user_id=<uuid>

Response:
{
  "trades": [
    { id, user_id, symbol, entry_price, ... }
  ]
}
```

#### GET /trades/{trade_id}
Get single trade
```
Authorization: Bearer <jwt_token>

Response:
{
  "trade": { id, user_id, symbol, ... }
}
```

#### PUT /trades/{trade_id}
Update trade
```
Authorization: Bearer <jwt_token>

Body: {
  symbol: "NIFTY",     // optional
  status: "closed",    // optional
  exit_price: 23200,   // optional
  pnl: 200,           // optional
  ...
}

Response:
{ "status": "updated" }
```

#### POST /trades/{trade_id}/close
Mark trade as closed with P&L
```
Authorization: Bearer <jwt_token>

Body: {
  exit_price: 23200,
  pnl: 200,
  status: "closed"  // optional, default "closed"
}

Response:
{ "status": "closed" }
```

#### DELETE /trades/{trade_id}
Delete trade
```
Authorization: Bearer <jwt_token>

Response:
{ "status": "deleted" }
```

---

### Watchlist Alerts

#### POST /alerts
Create watchlist alert
```
Authorization: Bearer <jwt_token>

Body: {
  symbol: "NIFTY",
  alert_type: "above",           // or "below", "pct_change"
  target_price: 24000,           // required if not pct_change
  pct_change: 2.5,              // required if type is pct_change
  base_price: 23000,            // optional, for pct_change
  is_active: true,
  repeat_mode: "one_shot",       // or "repeating"
  notify_telegram: true,
  notify_groww: false,
  notes: "..."
}

Response:
{ "status": "created" }
```

#### GET /alerts
List alerts
```
Authorization: Bearer <jwt_token>

Query params: 
  ?user_id=<uuid>
  ?active_only=true|false

Response:
{
  "alerts": [...],
  "count": 5,
  "active": 3,
  "triggered": 2
}
```

#### PUT /alerts/{alert_id}
Update alert
```
Authorization: Bearer <jwt_token>

Body: {
  symbol: "NIFTY",          // optional
  alert_type: "below",      // optional
  target_price: 23000,      // optional
  is_active: false,         // optional
  notes: "..."              // optional
}

Response:
{ "status": "updated" }
```

#### DELETE /alerts/{alert_id}
Delete alert
```
Authorization: Bearer <jwt_token>

Response:
{ "status": "deleted" }
```

#### POST /alerts/{alert_id}/reset
Reset triggered flag
```
Authorization: Bearer <jwt_token>

Response:
{ "status": "reset" }
```

#### POST /alerts/{alert_id}/toggle
Toggle alert active/inactive
```
Authorization: Bearer <jwt_token>

Response:
{
  "status": "toggled",
  "is_active": true
}
```

---

### Briefing Integration

#### POST /alerts/from-briefing
Create alerts from briefing research (authenticated with API key)
```
Authorization: Bearer sk-briefing-<key>

Body: [
  {
    "symbol": "NIFTY",
    "alert_type": "above",
    "target_price": 24500,
    "description": "Breakout level",
    "notes": "Expected resistance"
  }
]

Response:
{
  "status": "completed",
  "created": [...],
  "skipped": [...],
  "total": 2
}
```

---

## Schemas (Pydantic Models)

### TradeCreate
```python
class TradeCreate(BaseModel):
    symbol: str  # 1-20 chars
    entry_price: float  # > 0
    target_price: Optional[float] = None  # > 0
    stop_loss: Optional[float] = None  # > 0
    quantity: int  # > 0
    trade_type: Optional[str] = "long"  # pattern: ^(long|short)$
    status: Optional[str] = "pending"  # pattern: ^(pending|open|closed)$
    notes: Optional[str] = None  # max 500 chars
```

**⚠️ ISSUE:** Doesn't match Supabase table schema (missing 30+ fields)

### AlertCreate
```python
class AlertCreate(BaseModel):
    symbol: str  # 1-20 chars
    alert_type: str  # pattern: ^(above|below|pct_change)$
    target_price: Optional[float] = None  # > 0
    pct_change: Optional[float] = None  # > 0
    base_price: Optional[float] = None  # > 0, ⚠️ needed for pct_change
    is_active: Optional[bool] = True
    notify_telegram: Optional[bool] = True
    repeat_mode: Optional[str] = "one_shot"  # pattern: ^(one_shot|repeating)$
    notes: Optional[str] = None
```

---

## Environment Variables

```env
# Groww
GROWW_API_KEY=<key>
GROWW_API_SECRET=<secret>
GROWW_TOTP_SECRET=<totp>

# Telegram
TELEGRAM_BOT_TOKEN=<token>
TELEGRAM_CHAT_ID=<chat_id>        # Personal chat for commands
TELEGRAM_CHANNEL_ID=<channel_id>   # Broadcast channel

# Supabase
SUPABASE_URL=https://...
SUPABASE_SERVICE_KEY=...
SUPABASE_PUBLISHABLE_KEY=...  # Optional, not used

# App
PORT=8000
ENV=production
LOG_LEVEL=INFO
BRIEFING_API_KEY=sk-briefing-...
```

---

## Error Handling

All errors return JSON:
```json
{
  "detail": "Human-readable error message"
}
```

Common HTTP Status Codes:
- **200** - Success
- **201** - Created
- **400** - Bad Request (validation error)
- **401** - Unauthorized (missing/invalid token)
- **403** - Forbidden (insufficient permissions)
- **404** - Not Found
- **500** - Server Error

---

## Testing with curl

```bash
# Get fresh JWT from browser DevTools → Application → Local Storage → supabase.auth...

# Create trade
curl -X POST http://localhost:8000/trades \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{"symbol":"NIFTY","entry_price":23000,"quantity":1}'

# List trades
curl -X GET http://localhost:8000/trades \
  -H "Authorization: Bearer <your_jwt_token>"

# Create alert
curl -X POST http://localhost:8000/alerts \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{"symbol":"NIFTY","alert_type":"above","target_price":24000}'
```

---

## Known Issues & Limitations

1. **Trade Schema Too Minimal** - TradeCreate doesn't match table schema
2. **No Input Sanitization** - Text fields not escaped (could have SQL injection risk if directly used, but Supabase parameterizes)
3. **Watchlist Alerts Stateless** - No in-memory caching, reloads from DB for each request
4. **No Rate Limiting** - Anyone with valid JWT can spam requests
5. **Service Key Used for All Operations** - Bypasses RLS, no per-user isolation at DB level (relies on app code)

---

## Next Steps

1. ✅ Fix TradeCreate schema to match Supabase table
2. ✅ Add validation for pct_change alerts (require base_price)
3. ✅ Update PUT /alerts to use AlertUpdate schema
4. ✅ Add rate limiting per user
5. ✅ Add logging for all operations
6. ✅ Add integration tests
