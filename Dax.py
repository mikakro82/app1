#!/usr/bin/env python3
"""
Dax.py – Läuft als Headless-Service oder GUI.
Automatische Umrechnung von XDAXI auf GDAXI für Telegram-Signale.
Beendet sich selbst nach 50 Sekunden Laufzeit.
"""
import os
import time
import threading
from datetime import datetime

# GUI-Verfügbarkeit prüfen
try:
    import tkinter as tk
    if os.name != 'nt' and not os.environ.get('DISPLAY'):
        print("✨ Keine Anzeige gefunden - wechsle in den Headless-Modus.")
        GUI_AVAILABLE = False
    else:
        GUI_AVAILABLE = True
except ImportError:
    print("⚠️ tkinter nicht verfügbar - Headless-Modus aktiviert.")
    GUI_AVAILABLE = False

import yfinance as yf
from strategy_fvg_xdax_l_full_extended import (
    evaluate_fvg_strategy_with_result,
    run_with_monitoring
)
from telegram_notifier import send_telegram_signal

# Timer zum Beenden nach 50 Sekunden
def schedule_exit(root=None):
    if root:
        root.after(50000, root.destroy)
    else:
        threading.Timer(50, lambda: os._exit(0)).start()

# Echtzeit DAX-Kurs (GDAXI) abrufen
def get_real_dax():
    try:
        df = yf.download("^GDAXI", period="1d", interval="60m")
        return df["Close"].iloc[-1]
    except Exception:
        return None

# ==================== Headless-Modus ====================
def headless_run():
    schedule_exit()
    now = datetime.now().strftime('%H:%M:%S')
    print(f"[{now}] 🔍 Suche nach FVG-Signal...")
    try:
        result = evaluate_fvg_strategy_with_result()
    except Exception as e:
        print(f"[{now}] ❌ Fehler Strategie-Auswertung: {e}")
        return

    if result:
        # Rohwerte ziehen und als Python-Float sichern
        raw_entry = result['entry']
        entry = float(raw_entry.item()) if hasattr(raw_entry, 'item') else float(raw_entry)
        raw_sl = result['sl']
        sl    = float(raw_sl.item())    if hasattr(raw_sl,    'item') else float(raw_sl)
        raw_tp = result['tp']
        tp    = float(raw_tp.item())    if hasattr(raw_tp,    'item') else float(raw_tp)
        typ   = result['typ']
        zeit  = result['zeit']

        real = get_real_dax()
        if real is not None:
            factor = real / entry
            ge = float(entry * factor)
            gs = float(sl    * factor)
            gt = float(tp    * factor)

            print(f"[{now}] 📈 XDAXI: {entry:.2f} | GDAXI: {ge:.2f}")
            try:
                send_telegram_signal(ge, gs, gt, typ, zeit)
                print(f"[{now}] 📤 Telegram (umgerechnet) gesendet.")
            except Exception as e:
                print(f"[{now}] ❌ Sendefehler: {e}")
        else:
            print(
                f"[{now}] ⚠️ Kein GDAXI verfügbar - "
                f"sende XDAXI-Signal: Entry={entry:.2f}, SL={sl:.2f}, TP={tp:.2f}"
            )
            send_telegram_signal(entry, sl, tp, typ, zeit)
    else:
        print(f"[{now}] ℹ️ Kein neues Signal.")

    print(f"[{now}] 📡 Überprüfe aktive Trades...")
    try:
        run_with_monitoring()
        print(f"[{now}] ✅ Monitoring abgeschlossen.")
    except Exception as e:
        print(f"[{now}] ❌ Monitoring-Fehler: {e}")

# ==================== GUI-Modus ====================
if GUI_AVAILABLE:
    class DAXFVGApp:
        def __init__(self, root):
            self.root = root
            self.root.title("📈 DAX FVG Bot – Live & Monitoring")
            self.root.geometry("800x600")
            self.output = tk.Text(root, wrap=tk.WORD, height=30)
            self.output.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
            self.start_button = tk.Button(
                root, text="🟢 Einmal-Run", command=self.run_once
            )
            self.start_button.pack(pady=5)
            self.running = False

        def log(self, msg):
            t = datetime.now().strftime('%H:%M:%S')
            self.output.insert(tk.END, f"[{t}] {msg}\n")
            self.output.see(tk.END)

        def run_once(self):
            if not self.running:
                self.running = True
                self.start_button.config(state=tk.DISABLED)
                schedule_exit(self.root)
                threading.Thread(target=self.task, daemon=True).start()

        def task(self):
            self.log("🔍 Suche nach FVG-Signal...")
            try:
                result = evaluate_fvg_strategy_with_result()
            except Exception as e:
                self.log(f"❌ Fehler Strategie: {e}")
                return

            if result:
                raw_entry = result['entry']
                entry = float(raw_entry.item()) if hasattr(raw_entry, 'item') else float(raw_entry)
                raw_sl = result['sl']
                sl    = float(raw_sl.item())    if hasattr(raw_sl,    'item') else float(raw_sl)
                raw_tp = result['tp']
                tp    = float(raw_tp.item())    if hasattr(raw_tp,    'item') else float(raw_tp)
                typ   = result['typ']
                zeit  = result['zeit']
                real  = get_real_dax()

                if real is not None:
                    factor = real / entry
                    ge = float(entry * factor)
                    gs = float(sl    * factor)
                    gt = float(tp    * factor)
                    self.log(f"GDAXI: {real:.2f}, Signal GDAXI: {ge:.2f}")
                    send_telegram_signal(ge, gs, gt, typ, zeit)
                    self.log("📤 Telegram (GDAXI) gesendet.")
                else:
                    self.log(
                        f"⚠️ Kein GDAXI – sende XDAXI: "
                        f"Entry={entry:.2f}, SL={sl:.2f}, TP={tp:.2f}"
                    )
                    send_telegram_signal(entry, sl, tp, typ, zeit)
            else:
                self.log("ℹ️ Kein Signal.")

            self.log("📡 Trades prüfen...")
            try:
                run_with_monitoring()
                self.log("✅ Monitoring fertig.")
            except Exception as e:
                self.log(f"❌ Monitoring-Fehler: {e}")

    def run_gui():
        root = tk.Tk()
        app = DAXFVGApp(root)
        root.mainloop()

# ============ Programmstart ============
if __name__ == "__main__":
    if GUI_AVAILABLE:
        run_gui()
    else:
        headless_run()
