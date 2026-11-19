#!/usr/bin/env python3
"""Haftalık leaderboard (GitHub Actions, Cuma 16:31). Ortam: SLACK_BOT_TOKEN, RAW_CHANNEL, WEBHOOK_URL."""
import datetime, json, os, subprocess, sys, time, urllib.parse, urllib.request
from zoneinfo import ZoneInfo
TZ = ZoneInfo("Europe/Istanbul")
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
today = os.environ.get("DAY") or datetime.datetime.now(TZ).date().isoformat()
png = os.path.join(root, "leaderboards", f"{today}.png")
if os.path.exists(png) and os.environ.get("FORCE") != "1":
    print("Bu hafta zaten paylaşılmış."); sys.exit(0)

def slack(method, **params):
    req = urllib.request.Request(f"https://slack.com/api/{method}?" + urllib.parse.urlencode(params),
                                 headers={"Authorization": "Bearer " + os.environ["SLACK_BOT_TOKEN"]})
    d = json.load(urllib.request.urlopen(req, timeout=30))
    if not d.get("ok"): raise SystemExit(f"Slack {method} hatası: {d.get('error')}")
    return d

oldest = datetime.datetime(2026, 11, 17, tzinfo=TZ).timestamp()
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
out = subprocess.run([sys.executable, os.path.join(root, "scripts", "leaderboard.py"), raw, today, png], capture_output=True, text=True, check=True)
os.remove(raw)
s = json.loads(out.stdout); print(json.dumps(s, ensure_ascii=False))
if not s["players"]: print("Veri yok."); sys.exit(0)

def git(*a): subprocess.run(["git", "-C", root, *a], check=True)
git("config", "user.name", "Kelime Masters Bot"); git("config", "user.email", "actions@users.noreply.github.com")
git("add", png); git("commit", "-m", f"{today} leaderboard"); git("push")
img = f"https://raw.githubusercontent.com/{os.environ['GITHUB_REPOSITORY']}/main/leaderboards/{today}.png?v={int(time.time())}"
for _ in range(12):
    try:
        if urllib.request.urlopen(img, timeout=15).status == 200: break
    except Exception: pass
    time.sleep(5)
text = "🏆 *Haftalık leaderboard* · " + " · ".join(f"{m} {t}" for m, t in zip(["🥇", "🥈", "🥉"], s["top"]))
body = {"text": text.replace("*", ""), "blocks": [
    {"type": "section", "text": {"type": "mrkdwn", "text": text}},
    {"type": "image", "image_url": img, "alt_text": "Kelime Masters leaderboard"}]}
req = urllib.request.Request(os.environ["WEBHOOK_URL"], data=json.dumps(body, ensure_ascii=False).encode(), headers={"Content-Type": "application/json"})
resp = urllib.request.urlopen(req, timeout=30).read().decode()
if resp != "ok": raise SystemExit("Webhook hatası: " + resp)
print("Paylaşıldı.")
