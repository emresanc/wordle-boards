#!/usr/bin/env python3
"""Kelime Masters haftalık leaderboard (yalnız extension verisi).
Kullanım: python3 leaderboard.py raw.txt bugün(YYYY-MM-DD) out.png
Oynadığı gün = o gün sonucu gelen; birincilik = o günün 1.'si (bilmiş olmak şartıyla).
Win rate = birincilik / oynadığı gün. Sıralama: win rate, birincilik, ort. deneme, ort. süre."""
import json, os, re, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wm16
from PIL import Image, ImageDraw

START = "2026-11-18"

def stats(text, today):
    byday = defaultdict(dict)
    for tok in re.findall(r"WM1 ([A-Za-z0-9+/=]+)", text):
        try: r = wm16.decode(tok)
        except Exception: continue
        n, d = r.get("n", "").strip(), r.get("d", "")
        if not n or n == "İsimsiz" or not (START <= d <= today): continue
        byday[d].setdefault(n.lower(), r)          # kişi başı günün ilk sonucu
    P = defaultdict(lambda: {"name": "", "played": 0, "wins": 0, "solved": 0, "tries": 0, "ms": 0})
    for d in sorted(byday):
        rs = sorted(byday[d].values(), key=lambda r: (r["s"] != "WIN", len(r["w"]) if r["s"] == "WIN" else 7, r["ms"]))
        for i, r in enumerate(rs):
            p = P[r["n"].strip().lower()]
            p["name"] = r["n"].strip(); p["played"] += 1
            if r["s"] == "WIN":
                p["solved"] += 1; p["tries"] += len(r["w"]); p["ms"] += r["ms"]
                if i == 0: p["wins"] += 1
    rows = list(P.values())
    for p in rows: p["rate"] = p["wins"] / p["played"]
    rows.sort(key=lambda p: (-p["rate"], -p["wins"],
                             p["tries"] / p["solved"] if p["solved"] else 99,
                             p["ms"] / p["solved"] if p["solved"] else 1e12, p["name"]))
    return rows, len(byday)

def render(rows, ndays, today, out):
    cols = [("", 70), ("Oyuncu", 300), ("Oyun", 120), ("Birincilik", 170), ("Win %", 140), ("Ort. deneme", 190), ("Ort. süre", 160)]
    W = 40 + sum(w for _, w in cols) + 40; RH = 58; H = 170 + RH * (len(rows) + 1) + 50
    im = Image.new("RGB", (W, H), wm16.BG); d = ImageDraw.Draw(im)
    y_, m, dd = today.split("-"); s_y, s_m, s_d = START.split("-")
    d.text((40, 30), "Kelime Masters · Leaderboard", font=wm16.font(36), fill=(255, 255, 255))
    d.text((40, 82), f"{int(s_d)} {wm16.AYLAR[int(s_m)-1]} – {int(dd)} {wm16.AYLAR[int(m)-1]}  ·  {ndays} gün  ·  Win % = birincilik / oynanan gün",
           font=wm16.font(18), fill=(170, 170, 170))
    y = 140; x = 40
    for h, w in cols:
        d.text((x, y), h, font=wm16.font(20), fill=(170, 170, 170)); x += w
    y += RH - 10; d.line([(40, y - 8), (W - 40, y - 8)], fill=(58, 58, 60), width=2)
    medal = {0: (201, 176, 55), 1: (180, 180, 180), 2: (173, 138, 86)}
    for i, p in enumerate(rows):
        x = 40
        if i in medal: d.ellipse([x + 4, y + 4, x + 40, y + 40], fill=medal[i])
        d.text((x + 14 if i < 9 else x + 8, y + 9), str(i + 1), font=wm16.font(20), fill=(18, 18, 19) if i in medal else (255, 255, 255)); x += cols[0][1]
        avg_t = f"{p['tries']/p['solved']:.1f}" if p["solved"] else "–"
        avg_s = wm16.fmt(p["ms"] / p["solved"]) if p["solved"] else "–"
        vals = [p["name"], str(p["played"]), str(p["wins"]), f"%{round(p['rate']*100)}", avg_t, avg_s]
        for (h, w), v in zip(cols[1:], vals):
            col = (83, 141, 78) if h == "Win %" else (255, 255, 255)
            d.text((x, y + 8), v, font=wm16.font(24), fill=col); x += w
        y += RH
    im.save(out)

if __name__ == "__main__":
    text = open(sys.argv[1], encoding="utf-8").read(); today = sys.argv[2]
    rows, nd = stats(text, today)
    if rows: render(rows, nd, today, sys.argv[3])
    print(json.dumps({"players": len(rows), "days": nd, "top": [f"{p['name']} %{round(p['rate']*100)} ({p['wins']}/{p['played']})" for p in rows[:3]]}, ensure_ascii=False))
