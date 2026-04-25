#!/usr/bin/env python3
"""
Live OI monitoring via Groww Python SDK Feed API - Real-time expiry day hero/zero signals
Uses WebSocket for instant OI change detection (not polling)
Subscribes to key strikes and detects conviction shifts
"""

import os
import json
import time
from datetime import datetime
from typing import Optional, Dict, List, Callable
from collections import defaultdict
from dotenv import load_dotenv

# Load credentials
load_dotenv('/Users/sairam/madstreaks-backend/.env')
GROWW_TOKEN = os.getenv('GROWW_API_KEY')

try:
    from growwapi import GrowwAPI, GrowwFeed
except ImportError:
    print("❌ growwapi package not found")
    print("Install with: pip install growwapi")
    exit(1)

# Key levels for monitoring
KEY_LEVELS = {
    "support": [23500, 23700, 23800, 23900],
    "resistance": [24000, 24100, 24200, 24500],
}

# Thresholds
OI_CHANGE_THRESHOLD = 0.15  # 15% change = signal

# State tracking
oi_history = defaultdict(lambda: {"oi": 0, "ltp": 0, "timestamp": None})
signal_log = []
last_logged = defaultdict(lambda: {"time": 0, "signal": None})  # Rate limit alerts

def build_instrument_tokens() -> Dict[str, Dict]:
    """
    Build instrument tokens for all key strikes
    Format: {"exchange": "NSE", "segment": "DERIVATIVES", "token": "..."}

    For NIFTY options on 28-Apr-2026
    """
    instruments = {}

    # NIFTY option symbols and exchange tokens
    # Token format for NSE NIFTY options: varies by strike/expiry
    # Using instrument names as fallback - Groww SDK should resolve them

    expiry_str = "28APR26"

    for level_type, strikes in KEY_LEVELS.items():
        for strike in strikes:
            # PE instrument
            pe_key = f"NIFTY_{strike}PE_{expiry_str}"
            instruments[pe_key] = {
                "exchange": "NSE",
                "segment": "DERIVATIVES",
                "symbol": f"NIFTY{strike}PE{expiry_str}",
                "type": "PE",
                "strike": strike,
                "level": level_type
            }

            # CE instrument
            ce_key = f"NIFTY_{strike}CE_{expiry_str}"
            instruments[ce_key] = {
                "exchange": "NSE",
                "segment": "DERIVATIVES",
                "symbol": f"NIFTY{strike}CE{expiry_str}",
                "type": "CE",
                "strike": strike,
                "level": level_type
            }

    return instruments

def on_feed_data(meta: Dict, feed_obj: 'GrowwFeed'):
    """
    Callback when feed data arrives (real-time)

    Args:
        meta: Metadata about the feed update
        feed_obj: The GrowwFeed object to query for data
    """
    try:
        # Get LTP data for all subscribed instruments
        ltp_data = feed_obj.get_ltp()

        if not ltp_data or "ltp" not in ltp_data:
            return

        # Process NSE DERIVATIVES data
        nse_data = ltp_data.get("ltp", {}).get("NSE", {}).get("DERIVATIVES", {})

        signals = []
        current_time = datetime.now()

        for token, price_data in nse_data.items():
            ltp = price_data.get("ltp", 0)
            ts = price_data.get("tsInMillis", 0)

            # Find matching instrument from our watchlist
            for inst_key, inst_info in instruments.items():
                if token in inst_key or inst_info.get("symbol") == token:
                    strike = inst_info["strike"]
                    opt_type = inst_info["type"]
                    level = inst_info["level"]

                    # Track OI changes
                    oi_key = f"{opt_type}_{strike}"
                    prev_ltp = oi_history[oi_key]["ltp"]

                    # Store current LTP (using as proxy for OI change signal)
                    oi_history[oi_key]["ltp"] = ltp
                    oi_history[oi_key]["timestamp"] = ts

                    # === DETECT SIGNALS ===

                    # BULLISH: PE LTP drops at support (premiums declining = shorts covering)
                    if opt_type == "PE" and level == "support" and prev_ltp > 0:
                        ltp_change = (ltp - prev_ltp) / prev_ltp

                        # Sharp PE premium drop = shorts exiting = bullish
                        if ltp_change < -0.15:  # -15% drop
                            signal = {
                                "type": "BULLISH_HERO",
                                "strike": strike,
                                "level": level,
                                "option_type": opt_type,
                                "premium_change": f"{ltp_change*100:+.1f}%",
                                "current_ltp": ltp,
                                "prev_ltp": prev_ltp,
                                "action": f"BUY {strike-200} CE @ market",
                                "reason": f"PE premium dropped {ltp_change*100:.1f}% at support {strike} - shorts panic covering",
                                "time": current_time.strftime("%H:%M:%S")
                            }
                            signals.append(signal)

                    # BEARISH: CE LTP drops at resistance (call premium collapsing)
                    if opt_type == "CE" and level == "resistance" and prev_ltp > 0:
                        ltp_change = (ltp - prev_ltp) / prev_ltp

                        # Sharp CE premium drop = call shorts covering = bearish
                        if ltp_change < -0.15:  # -15% drop
                            signal = {
                                "type": "BEARISH_HERO",
                                "strike": strike,
                                "level": level,
                                "option_type": opt_type,
                                "premium_change": f"{ltp_change*100:+.1f}%",
                                "current_ltp": ltp,
                                "prev_ltp": prev_ltp,
                                "action": f"BUY {strike-300} PE @ market",
                                "reason": f"CE premium collapsed {ltp_change*100:.1f}% at resistance {strike} - breakout likely",
                                "time": current_time.strftime("%H:%M:%S")
                            }
                            signals.append(signal)

        # Process signals (rate-limited to avoid spam)
        for sig in signals:
            sig_key = f"{sig['strike']}_{sig['option_type']}"
            last_alert_time = last_logged[sig_key]["time"]

            # Rate limit: only alert once per minute per strike
            if (time.time() - last_alert_time) > 60:
                print(f"\n🎯 {sig['type']}")
                print(f"   Strike {sig['strike']}: {sig['option_type']} premium {sig['premium_change']}")
                print(f"   → {sig['action']}")
                print(f"   Reason: {sig['reason']}")

                send_telegram_alert(sig)
                signal_log.append(sig)
                last_logged[sig_key]["time"] = time.time()
                last_logged[sig_key]["signal"] = sig

    except Exception as e:
        print(f"❌ Feed callback error: {e}")

def send_telegram_alert(signal: Dict):
    """Send signal to Telegram"""
    try:
        import urllib.request
        import urllib.parse

        token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')

        emoji = "📈" if signal["type"] == "BULLISH_HERO" else "📉"
        message = f"""{emoji} <b>HERO/ZERO SIGNAL - {signal['type']}</b>

<b>Strike:</b> {signal['strike']} ({signal['level'].upper()})
<b>{signal['option_type']} Premium Change:</b> {signal['premium_change']}
<b>Current LTP:</b> ₹{signal['current_ltp']:.1f}
<b>Previous LTP:</b> ₹{signal['prev_ltp']:.1f}

<b>Action:</b> {signal['action']}
<b>Reason:</b> {signal['reason']}

<b>Time:</b> {signal['time']}"""

        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }

        data = urllib.parse.urlencode(payload).encode('utf-8')
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=data
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                print(f"✅ Telegram alert sent")
    except Exception as e:
        print(f"⚠️  Telegram failed: {e}")

def run_live_feed_monitor(duration_minutes: int = 360):
    """
    Run live OI monitoring via Groww Feed WebSocket

    Args:
        duration_minutes: How long to monitor (default 6 hours)
    """
    global instruments
    instruments = build_instrument_tokens()

    print("\n" + "="*70)
    print("🔴 LIVE OI MONITOR - GROWW FEED API (WebSocket)")
    print("="*70)
    print(f"Start time: {datetime.now().strftime('%H:%M:%S')}")
    print(f"Support levels: {KEY_LEVELS['support']}")
    print(f"Resistance levels: {KEY_LEVELS['resistance']}")
    print(f"Total instruments: {len(instruments)}")
    print(f"Signal threshold: {OI_CHANGE_THRESHOLD*100:.0f}% premium change")
    print(f"Duration: {duration_minutes} minutes")
    print("="*70 + "\n")

    if not GROWW_TOKEN:
        print("❌ GROWW_API_KEY not set in .env")
        return

    try:
        # Initialize Groww API and Feed
        print("🔗 Connecting to Groww Feed API...")
        groww = GrowwAPI(GROWW_TOKEN)
        feed = GrowwFeed(groww)

        print("✅ Connected to Groww Feed API\n")

        # Prepare instrument list for subscription
        # Groww SDK expects: [{"exchange": "NSE", "segment": "DERIVATIVES", "token": "..."}]
        instruments_list = [
            {
                "exchange": inst["exchange"],
                "segment": inst["segment"],
                "symbol": inst.get("symbol", "")
            }
            for inst in instruments.values()
        ]

        print(f"📡 Subscribing to {len(instruments_list)} instruments...\n")

        # Subscribe with callback (async mode)
        feed.subscribe_ltp(
            instruments_list,
            on_data_received=lambda meta: on_feed_data(meta, feed)
        )

        # Start consuming the feed (blocking call)
        print("🟢 Feed streaming... Press Ctrl+C to stop\n")
        start_time = time.time()

        try:
            feed.consume()
        except KeyboardInterrupt:
            print("\n\n⏹️  Feed stopped by user")

        elapsed = (time.time() - start_time) / 60

    except ImportError:
        print("❌ growwapi package not installed")
        print("   Install with: pip install growwapi")
    except Exception as e:
        print(f"❌ Feed error: {e}")
        import traceback
        traceback.print_exc()

    # Summary
    print(f"\n{'='*70}")
    print(f"✅ Monitor complete")
    print(f"Duration: {elapsed:.1f} minutes")
    print(f"Signals detected: {len(signal_log)}")

    if signal_log:
        print("\n📋 Signal Log:")
        for sig in signal_log:
            print(f"  {sig['time']}: {sig['type']} - Strike {sig['strike']}")

    print(f"{'='*70}\n")

if __name__ == "__main__":
    print("\n⚠️  This script uses Groww Python SDK Feed API")
    print("Install with: pip install growwapi\n")

    # Run for 6 hours (9:15 AM - 3:15 PM IST)
    run_live_feed_monitor(duration_minutes=360)
