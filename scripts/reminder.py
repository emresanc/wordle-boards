#!/usr/bin/env python3
"""Sabah hatırlatması (hafta içi 08:30). Salı–Cuma: günün ilk kelimesi bir önceki iş gününün cevabı.
Pazartesi serbest. Ortam: SLACK_BOT_TOKEN, RAW_CHANNEL, WEBHOOK_URL."""
import datetime, json, os, re, sys, urllib.parse, urllib.request
from zoneinfo import ZoneInfo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wm16
TZ = ZoneInfo("Europe/Istanbul")
today = datetime.datetime.now(TZ).date()
if os.environ.get("DAY"): today = datetime.date.fromisoformat(os.environ["DAY"])
if today.weekday() > 4: sys.exit(0)

MONDAY = ["Günaydın ☀️ Bugün pazartesi, ilk kelime serbest."]
OTHER = ["Günaydın ☀️ Bugünün ilk kelimesi: *{w}*"]

if today.weekday() == 0:
    text = MONDAY[today.toordinal() % len(MONDAY)]
else:
    prev = today - datetime.timedelta(days=1)
    oldest = datetime.datetime.combine(prev, datetime.time(), TZ).timestamp()
    req = urllib.request.Request("https://slack.com/api/conversations.history?" + urllib.parse.urlencode(
        {"channel": os.environ["RAW_CHANNEL"], "oldest": str(oldest), "limit": "200"}),
        headers={"Authorization": "Bearer " + os.environ["SLACK_BOT_TOKEN"]})
    d = json.load(urllib.request.urlopen(req, timeout=30))
    if not d.get("ok"): raise SystemExit("Slack hatası: " + str(d.get("error")))
    word = None
    for m in d.get("messages", []):
        for tok in re.findall(r"WM1 ([A-Za-z0-9+/=]+)", m.get("text", "")):
            try: r = wm16.decode(tok)
            except Exception: continue
            if r.get("d") == prev.isoformat() and r.get("a"): word = wm16.tr_upper(r["a"])
    if not word:
        print("Dünün cevabı bulunamadı (kimse oynamamış olabilir); mesaj atılmadı."); sys.exit(0)
    text = OTHER[today.toordinal() % len(OTHER)].format(w=word)

print(text)
if os.environ.get("DRY") == "1": sys.exit(0)
req = urllib.request.Request(os.environ["WEBHOOK_URL"], data=json.dumps({"text": text}, ensure_ascii=False).encode(),
                             headers={"Content-Type": "application/json"})
resp = urllib.request.urlopen(req, timeout=30).read().decode()
if resp != "ok": raise SystemExit("Webhook hatası: " + resp)
