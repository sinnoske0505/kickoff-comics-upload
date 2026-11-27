"""계정 시청자 분포(나이·국가·도시·성별) 확인 — 읽기 전용.
follower_demographics(팔로워), engaged_audience_demographics(반응한 사람) 를 받아 insights/audience.json 에 저장.
인스타 규칙상 팔로워/반응이 100명 미만이면 데이터가 비어 있을 수 있음."""
import os, json, datetime, urllib.request, urllib.parse, urllib.error
API = "https://graph.instagram.com/v23.0"; TOKEN = os.environ["IG_TOKEN"]
def get(path, **p):
    p["access_token"] = TOKEN
    try:
        with urllib.request.urlopen(f"{API}/{path}?{urllib.parse.urlencode(p)}", timeout=60) as r: return json.loads(r.read())
    except urllib.error.HTTPError as e: return {"error": e.read().decode()[:400]}
me = get("me", fields="user_id,username,followers_count")
uid = me.get("user_id") or me.get("id")
out = {"date": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(), "account": me, "data": {}}
for metric, extra in (("follower_demographics", {}), ("engaged_audience_demographics", {"timeframe": "this_month"}),
                      ("engaged_audience_demographics", {"timeframe": "last_90_days"}), ("reached_audience_demographics", {"timeframe": "this_month"})):
    for bd in ("age", "country", "city", "gender"):
        key = f"{metric}:{extra.get('timeframe','lifetime')}:{bd}"
        out["data"][key] = get(f"{uid}/insights", metric=metric, period="lifetime", metric_type="total_value", breakdown=bd, **extra)
# 최근 릴스 30일 계정 도달 합계도 참고용
out["data"]["reach_30d"] = get(f"{uid}/insights", metric="reach,views", period="day", metric_type="total_value",
    since=int((datetime.datetime.now()-datetime.timedelta(days=29)).timestamp()), until=int(datetime.datetime.now().timestamp()))
os.makedirs("insights", exist_ok=True)
json.dump(out, open("insights/audience.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False)[:3000])
