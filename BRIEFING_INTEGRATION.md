# Briefing-to-Alerts Integration

Automatically create Telegram alerts from research findings in `nse-briefing` or `stock-briefing` agents.

## Overview

When briefing agents find key support/resistance levels or breakout points, they can automatically create alerts in the watchlist. When price hits those levels during market hours, Telegram notifications are sent instantly.

## How It Works

```
nse-briefing/stock-briefing research
        ↓
Find key levels (breakout, support, resistance, targets)
        ↓
Call POST /alerts/from-briefing
        ↓
Alerts created in Supabase
        ↓
Groww feed monitors symbols
        ↓
Price hits level → Telegram alert sent
```

## API Endpoint

**POST** `https://web-production-f47c1.up.railway.app/alerts/from-briefing`

### Request Body

```json
[
  {
    "symbol": "NIFTY",
    "alert_type": "above",
    "target_price": 24500,
    "description": "ORB Breakout Level",
    "notes": "If breaks above with volume, target 25000"
  },
  {
    "symbol": "NIFTY",
    "alert_type": "above",
    "target_price": 25000,
    "description": "First Target",
    "notes": "Resistance from previous high"
  }
]
```

### Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `symbol` | string | ✅ | Stock/index symbol (NIFTY, TCS, BANKNIFTY, etc.) |
| `alert_type` | string | ✅ | `above`, `below`, or `pct_change` |
| `target_price` | number | ✅ | Price level to monitor |
| `description` | string | ❌ | Human-readable label (e.g., "ORB Breakout") |
| `notes` | string | ❌ | Additional context (e.g., "Target: 25000") |

### Response

```json
{
  "status": "completed",
  "created": [
    {
      "symbol": "NIFTY",
      "alert_type": "above",
      "target_price": 24500
    }
  ],
  "skipped": [],
  "total": 1
}
```

## Usage in Briefing Agents

### Option 1: Direct HTTP Call (Simple)

```python
import httpx

alerts = [
    {
        "symbol": "NIFTY",
        "alert_type": "above",
        "target_price": 24500,
        "description": "ORB Breakout",
        "notes": "Target: 25000"
    }
]

response = httpx.post(
    "https://web-production-f47c1.up.railway.app/alerts/from-briefing",
    json=alerts,
    timeout=10
)
print(response.json())
```

### Option 2: Using Helper Class (Recommended)

```python
from briefing_alerts_helper import BriefingAlertHelper

helper = BriefingAlertHelper(
    backend_url="https://web-production-f47c1.up.railway.app"
)

alerts = [
    {
        "symbol": "NIFTY",
        "alert_type": "above",
        "target_price": 24500,
        "description": "ORB Breakout",
        "notes": "If breaks above, expect 25000"
    },
    {
        "symbol": "NIFTY",
        "alert_type": "above",
        "target_price": 25000,
        "description": "First Target",
        "notes": "Resistance"
    }
]

result = helper.create_alerts_from_research(alerts)
# Prints: ✅ Created 2 alerts from briefing
```

## Example: Integration with nse-briefing

```python
# In nse-briefing.md agent execution

from briefing_alerts_helper import BriefingAlertHelper

# ... perform market analysis ...

# Extract key levels from analysis
breakout_level = 24500
target_1 = 25000
target_2 = 25500
support = 23500

# Create alerts for key levels
helper = BriefingAlertHelper()
research_alerts = [
    {
        "symbol": "NIFTY",
        "alert_type": "above",
        "target_price": breakout_level,
        "description": "ORB Breakout (15-min)",
        "notes": f"Entry: {breakout_level}, Target: {target_1}"
    },
    {
        "symbol": "NIFTY",
        "alert_type": "above",
        "target_price": target_1,
        "description": "First Target",
        "notes": f"Secondary target: {target_2}"
    },
    {
        "symbol": "NIFTY",
        "alert_type": "below",
        "target_price": support,
        "description": "Support / Stop Loss",
        "notes": "If broken, reversal likely"
    }
]

result = helper.create_alerts_from_research(research_alerts)

# Include in briefing output
print(f"\n📊 Alerts Created: {len(result['created'])}")
print(f"Watch for price action at: {breakout_level}, {target_1}, {target_2}")
```

## Alert Types

### `above` - Watch for price crossing ABOVE level

- Triggered when price ≥ target_price
- Useful for: Breakout levels, resistance breaks, targets
- Example: "NIFTY above 24500"

### `below` - Watch for price crossing BELOW level

- Triggered when price ≤ target_price
- Useful for: Support breaks, reversals, stop losses
- Example: "NIFTY below 23500"

### `pct_change` - Watch for percentage movement

- Triggered when price moves X% from base
- Requires: `base_price`, `pct_change` fields
- Example: "5% move from 24000"

## Features

✅ **Instant Notifications** - Telegram alert sent within seconds of price hit
✅ **Multi-level Monitoring** - Add multiple targets/levels in one call
✅ **Auto-subscribe** - Groww feed automatically subscribes to new symbols
✅ **Error Handling** - Invalid alerts skipped with clear error messages
✅ **Flexible Descriptions** - Add context that appears in Telegram messages

## Limitations

- Symbols must be valid NSE trading symbols (e.g., NIFTY, TCS, BANKNIFTY)
- Alerts active only during market hours (9:15 AM - 3:30 PM IST)
- Market must be open (weekdays only, excluding holidays)
- Each alert triggers once (one_shot mode) unless manually reset

## Debugging

### Check active alerts

```bash
curl https://web-production-f47c1.up.railway.app/watchlist
```

### Test endpoint locally

```bash
curl -X POST http://localhost:8000/alerts/from-briefing \
  -H "Content-Type: application/json" \
  -d '[{"symbol":"NIFTY","alert_type":"above","target_price":24500}]'
```

### Monitor Telegram notifications

Created alerts will send messages to your configured Telegram chat when triggered.

## Next Steps

1. Integrate helper into nse-briefing agent
2. Extract key levels from research findings
3. Call `/alerts/from-briefing` with extracted levels
4. Users receive instant Telegram alerts during market hours
