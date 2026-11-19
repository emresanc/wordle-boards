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
early = os.environ.get("EARLY") == "1"   # 16:00'dan önceki kontroller: yalnız herkes oynadıysa paylaş
ROSTER_DAYS = 7
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

day_start = datetime.datetime.fromisoformat(day).replace(tzinfo=TZ)
oldest = min(day_start - datetime.timedelta(days=ROSTER_DAYS), datetime.datetime(2026, 11, 18, tzinfo=TZ)).timestamp()
texts, cursor = [], None
while True:
    p = {"channel": os.environ["RAW_CHANNEL"], "oldest": str(oldest), "limit": "200"}
    if cursor: p["cursor"] = cursor
    d = slack("conversations.history", **p)
    texts += [m.get("text", "") for m in d.get("messages", [])]
    cursor = (d.get("response_metadata") or {}).get("next_cursor")
    if not cursor: break
if early:
    sys.path.insert(0, os.path.join(root, "scripts"))
    import re, wm16
    names_by_day = {}
    for tok in re.findall(r"WM1 ([A-Za-z0-9+/=]+)", "\n".join(texts)):
        try: r = wm16.decode(tok)
        except Exception: continue
        n = r.get("n", "").strip()
        if n and n != "İsimsiz": names_by_day.setdefault(r.get("d"), set()).add(n.lower())
    today_names = names_by_day.get(day, set())
    since = (day_start - datetime.timedelta(days=ROSTER_DAYS)).date().isoformat()
    since = max(since, "2026-11-18")   # öncesi test günleri
    roster = set().union(*[v for d, v in names_by_day.items() if d != day and d >= since] or [set()]) | today_names
    missing = roster - today_names
    print(f"Bugün oynayan {len(today_names)}/{len(roster)}; bekleniyor: {sorted(missing)}")
    if len(roster) < 2 or missing:
        print("Herkes bitirmedi, 16:00 bekleniyor."); sys.exit(0)
    print("Herkes bitirdi, erken paylaşılıyor.")
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
head = "🟩 *Herkes bitirdi!* " if early else "🟩 "
text = head + f"*Günün sonuçları* · Cevap: {s['answer']} · {s['count']} oyuncu\n" + "\n".join(f"{medals[i]} {r}" for i, r in enumerate(s["ranking"][:3]))
body = {"text": text.replace("*", ""), "blocks": [
    {"type": "section", "text": {"type": "mrkdwn", "text": text}},
    {"type": "image", "image_url": img, "alt_text": "Günün Wordle tahtaları"}]}
def post_webhook(payload):
    req = urllib.request.Request(os.environ["WEBHOOK_URL"], data=json.dumps(payload, ensure_ascii=False).encode(), headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req, timeout=30).read().decode()
    if resp != "ok": raise SystemExit("Webhook hatası: " + resp)

def post_bot(payload):
    req = urllib.request.Request("https://slack.com/api/chat.postMessage", data=json.dumps(payload, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json; charset=utf-8", "Authorization": "Bearer " + os.environ["SLACK_BOT_TOKEN"]})
    d = json.load(urllib.request.urlopen(req, timeout=30))
    if not d.get("ok"): raise RuntimeError(d.get("error"))
    return d["ts"]

ts = None
chan = os.environ.get("RESULT_CHANNEL")
if chan:
    try: ts = post_bot({"channel": chan, **body})
    except Exception as e: print("Bot ile gönderilemedi, webhook'a düşülüyor:", e)
if not ts: post_webhook(body)
print("Paylaşıldı.")

# Genel durum (leaderboard) thread'e
if ts:
    try:
        allraw = os.path.join(root, "all.tmp"); open(allraw, "w", encoding="utf-8").write("\n".join(texts))
        lb = os.path.join(root, "leaderboards", "daily", f"{day}.png"); os.makedirs(os.path.dirname(lb), exist_ok=True)
        o = subprocess.run([sys.executable, os.path.join(root, "scripts", "leaderboard.py"), allraw, day, lb], capture_output=True, text=True, check=True)
        os.remove(allraw); ls = json.loads(o.stdout)
        if ls["players"]:
            git("add", lb); git("commit", "-m", f"{day} genel durum"); git("push")
            lbimg = f"https://raw.githubusercontent.com/{os.environ['GITHUB_REPOSITORY']}/main/leaderboards/daily/{day}.png?v={int(time.time())}"
            for _ in range(12):
                try:
                    if urllib.request.urlopen(lbimg, timeout=15).status == 200: break
                except Exception: pass
                time.sleep(5)
            post_bot({"channel": chan, "thread_ts": ts, "text": "🏆 Genel durum",
                      "blocks": [{"type": "image", "image_url": lbimg, "alt_text": "Genel durum", "title": {"type": "plain_text", "text": "🏆 Genel durum"}}]})
            print("Genel durum thread'e atıldı.")
    except Exception as e:
        print("Genel durum atılamadı:", e)
