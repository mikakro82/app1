import yfinance as yf
import pandas as pd
from datetime import datetime
from telegram_notifier import send_telegram_signal, update_signal_result, send_daily_summary

# 📈 ETF-Daten laden
def get_dax_etf_xdax(interval='60m'):
    try:
        ticker = yf.Ticker("XDAX.L")
        df = ticker.history(period="1d", interval=interval)
        if df.empty:
            print("⚠️ Keine Daten empfangen für XDAX.L.")
            return None
        df = df[['Open', 'High', 'Low', 'Close']]
        df.index = df.index.tz_convert('Europe/Berlin')
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {len(df)} Kerzen von XDAX.L geladen.")
        return df
    except Exception as e:
        print("❌ Fehler beim Laden der XDAX.L Daten:", e)
        return None

# 🧠 FVG-Erkennung (vereinfacht)
def detect_fvg(df):
    fvg_rows = []
    for i in range(1, len(df)-1):
        prev = df.iloc[i-1]
        next = df.iloc[i+1]
        if prev['High'] < next['Low']:
            fvg_rows.append((i, 'bullish', prev['High'], next['Low']))
        elif prev['Low'] > next['High']:
            fvg_rows.append((i, 'bearish', next['High'], prev['Low']))
    return fvg_rows

# 🔍 Strategie mit Signal-Rückgabe
def evaluate_fvg_strategy_with_result():
    df = get_dax_etf_xdax()
    if df is None or df.empty:
        return None

    # ⏰ Nur Zeitfenster 12:00–14:29 analysieren
    df = df.between_time("12:00", "14:29")
    fvg_list = detect_fvg(df)
    if not fvg_list:
        print("ℹ️ Kein FVG im Zeitfenster erkannt.")
        return None

    i, fvg_type, fvg_low, fvg_high = fvg_list[-1]  # letztes FVG im Zeitfenster
    if i + 1 >= len(df):
        return None

    entry = df['Close'].iloc[i+1]
    sl = fvg_low if fvg_type == 'bullish' else fvg_high
    tp = entry + 3 * abs(entry - sl) if fvg_type == 'bullish' else entry - 3 * abs(entry - sl)
    zeit = df.index[i+1].to_pydatetime()

    return {
        "entry": float(entry),
        "sl": float(sl),
        "tp": float(tp),
        "typ": fvg_type,
        "zeit": zeit
    }

# ▶️ Hauptfunktion: Monitoring + Telegram
def run_with_monitoring():
    df = get_dax_etf_xdax()
    if df is None or df.empty:
        return

    # 📤 Telegram-Signal senden, wenn erkannt
    result = evaluate_fvg_strategy_with_result()
    if result:
        send_telegram_signal(result)

    # 📊 Ergebnis prüfen mit letztem Kurs
    last_price = df['Close'].iloc[-1]
    update_signal_result(last_price)

    # 🕔 Tägliche Zusammenfassung um 17:00
    now = datetime.now()
    if now.strftime("%H:%M") == "17:00":
        send_daily_summary()

if __name__ == "__main__":
    run_with_monitoring()
