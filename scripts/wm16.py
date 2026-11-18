#!/usr/bin/env python3
"""Kelime Masters 16:00 sıralaması.
Kullanım: python3 wm16.py raw.txt YYYY-MM-DD out.png
raw.txt: #wordle-raw mesajlarının metni (WM1 ... satırları içeren herhangi bir metin).
Çıktı: out.png ve stdout'a JSON özet (oyuncu sayısı, cevap, sıralama).
"""
import base64, json, re, sys
from PIL import Image, ImageDraw, ImageFont

KEY = b"kelime-masters"
AYLAR = ["Ocak","Şubat","Mart","Nisan","Mayıs","Haziran","Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"]

def decode(tok):
    raw = base64.b64decode(tok)
    return json.loads(bytes(b ^ KEY[i % len(KEY)] for i, b in enumerate(raw)).decode("utf-8"))

def tr_upper(s):
    return s.replace("i", "İ").replace("ı", "I").upper()

def font(sz):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]:
        try: return ImageFont.truetype(p, sz)
        except OSError: pass
    return ImageFont.load_default()

COL = {"c": (83,141,78), "p": (181,159,59), "a": (58,58,60)}
BG = (18,18,19); EMPTY = (58,58,60)

def fmt(ms):
    s = round(ms / 1000); return f"{s//60}:{s%60:02d}"

def collect(text, day):
    seen, out = set(), []
    for tok in re.findall(r"WM1 ([A-Za-z0-9+/=]+)", text):
        try: r = decode(tok)
        except Exception: continue
        if r.get("d") != day or not r["n"].strip() or r["n"].strip() == "İsimsiz" or r["n"].strip().lower() in seen: continue
        seen.add(r["n"].strip().lower()); out.append(r)
    # Kazananlar: az deneme, sonra kısa süre. Bilemeyenler en sonda.
    out.sort(key=lambda r: (r["s"] != "WIN", len(r["w"]) if r["s"] == "WIN" else 7, r["ms"]))
    return out

def render(results, day, out):
    T, G, PAD, PER_ROW = 56, 6, 40, 5
    bw, bh = 5*T + 4*G, 6*T + 5*G
    cols = min(PER_ROW, len(results)); rows = -(-len(results) // PER_ROW)
    blockh = 100 + bh + PAD
    W = PAD + cols * (bw + PAD); H = 90 + rows * blockh
    im = Image.new("RGB", (max(W, 620), H), BG); d = ImageDraw.Draw(im)
    y, m, dd = day.split("-")
    d.text((PAD, 28), f"{int(dd)} {AYLAR[int(m)-1]}  ·  Cevap: {tr_upper(results[0]['a'])}", font=font(30), fill=(255,255,255))
    for i, r in enumerate(results):
        x0 = PAD + (i % PER_ROW) * (bw + PAD); top = 90 + (i // PER_ROW) * blockh
        tries = f"{len(r['w'])}/6" if r["s"] == "WIN" else "X/6"
        d.text((x0, top), f"{i+1}. {r['n']}", font=font(24), fill=(255,255,255))
        d.text((x0, top + 30), f"{tries}  ·  {fmt(r['ms'])}", font=font(18), fill=(170,170,170))
        y0 = top + 60
        for row in range(6):
            for c in range(5):
                x = x0 + c*(T+G); yy = y0 + row*(T+G)
                if row < len(r["w"]):
                    d.rectangle([x, yy, x+T, yy+T], fill=COL.get(r["e"][row][c], COL["a"]))
                    ch = tr_upper(r["w"][row][c]); f = font(30); bb = d.textbbox((0,0), ch, font=f)
                    d.text((x + (T-(bb[2]-bb[0]))/2 - bb[0], yy + (T-(bb[3]-bb[1]))/2 - bb[1]), ch, font=f, fill=(255,255,255))
                else:
                    d.rectangle([x, yy, x+T, yy+T], outline=EMPTY, width=2)
    im.save(out)

if __name__ == "__main__":
    text = open(sys.argv[1], encoding="utf-8").read(); day = sys.argv[2]; out = sys.argv[3]
    res = collect(text, day)
    if res: render(res, day, out)
    print(json.dumps({"count": len(res), "answer": tr_upper(res[0]["a"]) if res else None,
        "winner": res[0]["n"].strip() if res and res[0]["s"] == "WIN" else None,
        "ranking": [f"{r['n']} {(str(len(r['w'])) if r['s']=='WIN' else 'X')}/6 {fmt(r['ms'])}" for r in res]}, ensure_ascii=False))
