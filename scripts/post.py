"""킥오프코믹스 인스타 자동 업로드.
posts/<폴더>/ 안에 1.jpg, 2.jpg ... + caption.txt + (선택) post_at.txt(한국시간 'YYYY-MM-DD HH:MM')
아직 안 올라간 폴더 중 시간이 된 것을 캐러셀로 올리고 posted.txt 를 남긴다.
"""
import os, sys, time, json, glob, datetime, urllib.request, urllib.parse

API = "https://graph.instagram.com/v23.0"
TOKEN = os.environ["IG_TOKEN"]
REPO = os.environ.get("GITHUB_REPOSITORY", "sinnoske0505/kickoff-comics-upload")
BRANCH = os.environ.get("GITHUB_REF_NAME", "main")
ONLY = os.environ.get("ONLY_POST", "").strip()
KST = datetime.timezone(datetime.timedelta(hours=9))

def call(method, path, **params):
    params["access_token"] = TOKEN
    data = urllib.parse.urlencode(params).encode()
    if method == "GET":
        req = urllib.request.Request(f"{API}/{path}?{data.decode()}")
    else:
        req = urllib.request.Request(f"{API}/{path}", data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print("API 오류:", e.code, e.read().decode()[:500]); raise

def wait_ready(cid):
    for _ in range(30):
        s = call("GET", cid, fields="status_code").get("status_code")
        if s == "FINISHED": return
        if s in ("ERROR", "EXPIRED"): raise RuntimeError(f"컨테이너 {cid} 상태 {s}")
        time.sleep(10)
    raise RuntimeError("시간 초과")

def publish(folder):
    imgs = sorted(glob.glob(f"{folder}/*.jpg"), key=lambda p: int(os.path.basename(p).split('.')[0]))
    caption = open(f"{folder}/caption.txt", encoding="utf-8").read().strip()
    me = call("GET", "me", fields="user_id,username")
    uid = me["user_id"]; print("계정:", me.get("username"))
    url = lambda p: f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{p}"
    if len(imgs) == 1:
        c = call("POST", f"{uid}/media", image_url=url(imgs[0]), caption=caption, is_ai_generated="true")["id"]
    else:
        kids = []
        for p in imgs:
            k = call("POST", f"{uid}/media", image_url=url(p), is_carousel_item="true")["id"]
            wait_ready(k); kids.append(k)
        c = call("POST", f"{uid}/media", media_type="CAROUSEL", children=",".join(kids), caption=caption, is_ai_generated="true")["id"]
    wait_ready(c)
    res = call("POST", f"{uid}/media_publish", creation_id=c)
    link = call("GET", res["id"], fields="permalink").get("permalink", "")
    open(f"{folder}/posted.txt", "w").write(f"{datetime.datetime.now(KST):%Y-%m-%d %H:%M} {link}\n")
    print("게시 완료:", link)

now = datetime.datetime.now(KST)
done = 0
for folder in sorted(glob.glob("posts/*/")):
    folder = folder.rstrip("/")
    if os.path.exists(f"{folder}/posted.txt"): continue
    if ONLY and os.path.basename(folder) != ONLY: continue
    if not ONLY and os.path.exists(f"{folder}/post_at.txt"):
        t = datetime.datetime.strptime(open(f"{folder}/post_at.txt").read().strip(), "%Y-%m-%d %H:%M").replace(tzinfo=KST)
        if t > now: print("대기:", folder, t); continue
    elif not ONLY:
        continue  # 시간 없는 폴더는 직접 실행할 때만
    publish(folder); done += 1
print("이번 실행 게시 수:", done)
