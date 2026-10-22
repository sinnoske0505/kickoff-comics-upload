"""킥오프코믹스 주간 성과 분석 (ig-audit 방식).

인스타 공식 API로 최근 게시물 인사이트를 받아서
조회수 대신 '평소 대비 몇 배'(outlier), 보내기/도달, 저장/도달, 팔로우/도달로 순위를 매깁니다.
결과: insights/latest.md (사람이 읽는 표), insights/YYYY-MM-DD.json (원자료)
게시·댓글 등 계정 행동은 하지 않습니다(읽기 전용).
"""
import os, json, glob, datetime, statistics, urllib.request, urllib.parse, urllib.error

API = "https://graph.instagram.com/v23.0"
TOKEN = os.environ["IG_TOKEN"]
KST = datetime.timezone(datetime.timedelta(hours=9))
METRICS = ["views", "reach", "likes", "comments", "shares", "saved", "total_interactions",
           "follows", "profile_visits", "ig_reels_avg_watch_time"]


def get(path, **params):
    params["access_token"] = TOKEN
    url = f"{API}/{path}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode()[:300]}


def insights(mid):
    """지표를 하나씩 요청(게시물 종류마다 지원 지표가 달라서)."""
    out = {}
    for m in METRICS:
        res = get(f"{mid}/insights", metric=m)
        for d in res.get("data", []):
            v = d.get("values", [{}])[0].get("value", d.get("total_value", {}).get("value"))
            if v is not None:
                out[m] = v
    return out


def folder_map():
    """permalink → posts 폴더 이름."""
    m = {}
    for f in glob.glob("posts/*/posted.txt"):
        for line in open(f, encoding="utf-8"):
            for tok in line.split():
                if tok.startswith("https://www.instagram.com/"):
                    m[tok.rstrip("/").split("/")[-1]] = os.path.basename(os.path.dirname(f))
    return m


def main():
    me = get("me", fields="user_id,username,followers_count,media_count")
    media = get("me/media", fields="id,caption,media_type,media_product_type,permalink,timestamp", limit=50).get("data", [])
    fmap = folder_map()
    rows = []
    for md in media:
        ins = insights(md["id"])
        code = md.get("permalink", "").rstrip("/").split("/")[-1]
        rows.append({
            "id": md["id"], "kind": "REELS" if md.get("media_product_type") == "REELS" else md.get("media_type"),
            "folder": fmap.get(code, ""), "permalink": md.get("permalink"),
            "time": md.get("timestamp"), "first_line": (md.get("caption") or "").split("\n")[0][:90],
            **ins})
    # 종류별 중앙값 대비 배수
    for kind in {r["kind"] for r in rows}:
        grp = [r for r in rows if r["kind"] == kind and r.get("views") is not None]
        med = statistics.median([r["views"] for r in grp]) if grp else 0
        for r in grp:
            r["outlier"] = round(r["views"] / med, 2) if med else None
    for r in rows:
        reach = r.get("reach") or 0
        for k, name in [("shares", "send_rate"), ("saved", "save_rate"), ("follows", "follow_rate")]:
            r[name] = round(r[k] * 1000 / reach, 1) if reach and r.get(k) is not None else None  # 도달 1,000명당

    today = datetime.datetime.now(KST).strftime("%Y-%m-%d")
    os.makedirs("insights", exist_ok=True)
    json.dump({"account": me, "rows": rows}, open(f"insights/{today}.json", "w"), ensure_ascii=False, indent=1)

    def f(v):
        return "-" if v is None else str(v)
    lines = [f"# 킥오프코믹스 성과 ({today} KST)", "",
             f"팔로워 {f(me.get('followers_count'))} · 게시물 {f(me.get('media_count'))}", "",
             "순위 기준: 평소 대비 배수(outlier, 같은 종류 중앙값 대비) → 보내기/도달. 조회수 자체는 참고만.", "",
             "| 종류 | 편 | 게시 | 조회 | 도달 | 배수 | 보내기/1천 | 저장/1천 | 팔로우/1천 | 댓글 | 평균시청(ms) |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    rows.sort(key=lambda r: (-(r.get("outlier") or 0), -(r.get("send_rate") or 0)))
    for r in rows:
        name = r["folder"] or r["first_line"][:30]
        lines.append(f"| {r['kind']} | [{name}]({r['permalink']}) | {(r['time'] or '')[:10]} | {f(r.get('views'))} | {f(r.get('reach'))} | "
                     f"{f(r.get('outlier'))} | {f(r.get('send_rate'))} | {f(r.get('save_rate'))} | {f(r.get('follow_rate'))} | "
                     f"{f(r.get('comments'))} | {f(r.get('ig_reels_avg_watch_time'))} |")
    if "error" in me:
        lines += ["", f"계정 정보 오류: {me['error']}"]
    open("insights/latest.md", "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines))


main()
