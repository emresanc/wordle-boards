#!/usr/bin/env python3
"""Kelime Masters günlük paylaşım (GitHub Actions).
#wordle-raw'ı Slack API ile okur, tahtaları çizer, repoya ekler, Wordle Bot webhook'u ile #wordlemasters'a atar.
Ortam: SLACK_BOT_TOKEN, RAW_CHANNEL, WEBHOOK_URL. Aynı gün ikinci kez paylaşmaz (boards/<gün>.png varsa)."""
import json, os, subprocess, sys, time, urllib.request, urllib.parse, datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Istanbul")
now = datetime.datetime.now(TZ)
day = os.environ.get("DAY") or now.date().isoformat()
force = os.environ.get("FORCE") == "1"
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
png = os.path.join(root, "boards", f"{day}.png")
if os.path.exists(png) and not force:
    print("Bugün zaten paylaşılmış:", day); sys.exit(0)

def slack(method, **params):
    url = f"https://slack.com/api/{method}?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + os.environ["SLACK_BOT_TOKEN"]})
    d = json.load(urllib.request.urlopen(req, timeout=30))
    if not d.get("ok"): raise SystemExit(f"Slack {method} hatası: {d.get('error')}")
    return d

oldest = datetime.datetime.fromisoformat(day).replace(tzinfo=TZ).timestamp()
texts, cursor = [], None
while True:
    p = {"channel": os.environ["RAW_CHANNEL"], "oldest": str(oldest), "limit": "200"}
    if cursor: p["cursor"] = cursor
    d = slack("conversations.history", **p)
    texts += [m.get("text", "") for m in d.get("messages", [])]
    cursor = (d.get("response_metadata") or {}).get("next_cursor")
    if not cursor: break
raw = os.path.join(root, "raw.tmp"); open(raw, "w", encoding="utf-8").write("\n".join(texts))
os.makedirs(os.path.dirname(png), exist_ok=True)
out = subprocess.run([sys.executable, os.path.join(root, "scripts", "wm16.py"), raw, day, png], capture_output=True, text=True, check=True)
os.remove(raw)
s = json.loads(out.stdout); print(json.dumps(s, ensure_ascii=False))
if not s["count"]: print("Bugün sonuç yok."); sys.exit(0)

def git(*a): subprocess.run(["git", "-C", root, *a], check=True)
git("config", "user.name", "Kelime Masters Bot"); git("config", "user.email", "actions@users.noreply.github.com")
git("add", png); git("commit", "-m", f"{day} tahtaları"); git("push")

img = f"https://raw.githubusercontent.com/{os.environ['GITHUB_REPOSITORY']}/main/boards/{day}.png?v={int(time.time())}"
for _ in range(12):
    try:
        if urllib.request.urlopen(img, timeout=15).status == 200: break
    except Exception: pass
    time.sleep(5)

medals = ["🥇", "🥈", "🥉"]
text = f"🟩 *Günün sonuçları* · Cevap: {s['answer']} · {s['count']} oyuncu\n" + "\n".join(f"{medals[i]} {r}" for i, r in enumerate(s["ranking"][:3]))
body = {"text": text.replace("*", ""), "blocks": [
    {"type": "section", "text": {"type": "mrkdwn", "text": text}},
    {"type": "image", "image_url": img, "alt_text": "Günün Wordle tahtaları"}]}
req = urllib.request.Request(os.environ["WEBHOOK_URL"], data=json.dumps(body, ensure_ascii=False).encode(), headers={"Content-Type": "application/json"})
resp = urllib.request.urlopen(req, timeout=30).read().decode()
if resp != "ok": raise SystemExit("Webhook hatası: " + resp)
print("Paylaşıldı.")
