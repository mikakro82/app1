import requests
from datetime import datetime, timedelta
import json
import os

BOT_TOKEN = "8170146997:AAE5P3SIi_L06iYkke35s7A1EP77KftkWVI"
CHAT_ID   = "1596720374"

LOG_FILE = "signal_log.json"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, data=data)
    except Exception as e:
        print("Telegram Error:", e)

def send_telegram_signal(entry, sl, tp, direction, time):
    risk     = abs(entry - sl)
    reward   = abs(tp - entry)
    rr_ratio = round(reward / risk, 2)
    sl_pct   = round((risk / entry) * 100, 2)
    tp_pct   = round((reward / entry) * 100, 2)

    message = (
        f"📊 *FVG {direction.upper()} Signal*\n"
        f"🕒 Zeit: {time}\n"
        f"🎯 Entry: `{entry:.2f}`\n"
        f"🛡️ SL: `{sl:.2f}` ({sl_pct}%)\n"
        f"🏁 TP: `{tp:.2f}` ({tp_pct}%)\n"
        f"📐 CRV: `{rr_ratio}:1`"
    )
    save_signal_log(time, entry, sl, tp)
    send_telegram_message(message)

def save_signal_log(time, entry, sl, tp):
    now = datetime.now().isoformat()
    result = {
        "time":        time.isoformat(),
        "entry":       entry,
        "sl":          sl,
        "tp":          tp,
        "status":      "pending",
        "triggered_at": None
    }

    data = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except:
                data = []

    data.append(result)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def update_signal_result(price_now):
    changed = False
    if not os.path.exists(LOG_FILE):
        return

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    for signal in data:
        if signal["status"] == "pending":
            if price_now >= signal["tp"]:
                signal["status"]       = "take_profit"
                signal["triggered_at"] = datetime.now().isoformat()
                send_telegram_message(f"✅ *Take Profit erreicht!* Entry: {signal['entry']} → TP: {signal['tp']}")
                changed = True
            elif price_now <= signal["sl"]:
                signal["status"]       = "stop_loss"
                signal["triggered_at"] = datetime.now().isoformat()
                send_telegram_message(f"🛑 *Stop Loss erreicht!* Entry: {signal['entry']} → SL: {signal['sl']}")
                changed = True

    if changed:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

def send_daily_summary():
    if not os.path.exists(LOG_FILE):
        send_telegram_message("📊 Keine Signal-Daten für die Tagesauswertung verfügbar.")
        return

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    now = datetime.now()
    stats = {
        "day":   {"tp": 0, "sl": 0},
        "week":  {"tp": 0, "sl": 0},
        "month": {"tp": 0, "sl": 0},
        "year":  {"tp": 0, "sl": 0}
    }

    for s in data:
        if s["status"] in ["take_profit", "stop_loss"]:
            t = datetime.fromisoformat(s["triggered_at"])
            for k, delta in [
                ("day",   timedelta(days=1)),
                ("week",  timedelta(weeks=1)),
                ("month", timedelta(days=31)),
                ("year",  timedelta(days=365)),
            ]:
                if now - t <= delta:
                    stats[k]["tp" if s["status"]=="take_profit" else "sl"] += 1

    message = (
        f"📈 *Tagesauswertung {now.strftime('%d.%m.%Y')}*\n"
        f"📅 Heute: ✅ {stats['day']['tp']} TP | 🛑 {stats['day']['sl']} SL\n"
        f"🗓️ Woche: ✅ {stats['week']['tp']} TP | 🛑 {stats['week']['sl']} SL\n"
        f"📆 Monat: ✅ {stats['month']['tp']} TP | 🛑 {stats['month']['sl']} SL\n"
        f"📊 Jahr: ✅ {stats['year']['tp']} TP | 🛑 {stats['year']['sl']} SL"
    )
    send_telegram_message(message)
