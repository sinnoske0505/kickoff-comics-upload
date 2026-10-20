"""킥오프코믹스 인스타 자동 업로드.

posts/<폴더>/ 안에
  1.jpg, 2.jpg ...      캐러셀 이미지 (순서대로)
  caption.txt           캡션
  post_at.txt           (선택) 한국시간 'YYYY-MM-DD HH:MM'
  alt.txt               (선택) 이미지별 대체 텍스트, 한 줄에 하나
  collab.txt            (선택) 공동 게시 초대할 계정 아이디, 한 줄에 하나 (최대 3)
아직 안 올라간 폴더 중 시간이 된 것을 올리고 posted.txt 를 남긴다.

매 게시마다 자동으로:
  - 캡션 규칙 맞추기: 해시태그 5개 제한, 면책 문구 확인
  - 이미지 대체 텍스트(alt.txt 없으면 캡션 첫 줄로 자동 생성)
  - 첫 댓글: 지난 편 MVP 투표 결과 집계 + 이번 편 투표 안내
  - 스토리에 첫 장 공유 (계정 유형상 안 되면 건너뜀)
"""
import os, re, sys, time, json, glob, datetime, collections, urllib.request, urllib.parse

API = "https://graph.instagram.com/v23.0"
TOKEN = os.environ["IG_TOKEN"]
REPO = os.environ.get("GITHUB_REPOSITORY", "sinnoske0505/kickoff-comics-upload")
BRANCH = os.environ.get("GITHUB_REF_NAME", "main")
ONLY = os.environ.get("ONLY_POST", "").strip()
KST = datetime.timezone(datetime.timedelta(hours=9))
MAX_TAGS = 5
DISCLAIMER = "Fan-made comic. Not affiliated with any club, league or player."
NUM_EMOJI = {"1": "1️⃣", "2": "2️⃣", "3": "3️⃣", "4": "4️⃣"}


class ApiError(Exception):
    pass


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
        body = e.read().decode()[:500]
        print("API 오류:", e.code, body)
        raise ApiError(body)


def wait_ready(cid):
    for _ in range(30):
        s = call("GET", cid, fields="status_code").get("status_code")
        if s == "FINISHED":
            return
        if s in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"컨테이너 {cid} 상태 {s}")
        time.sleep(10)
    raise RuntimeError("시간 초과")


# ---------- 캡션 규칙 ----------
def clean_caption(text):
    """해시태그는 앞에서부터 5개만(중복 제거), 면책 문구가 없으면 추가."""
    tags_seen, kept = [], 0

    def keep(m):
        nonlocal kept
        t = m.group(0)
        low = t.lower()
        if low in tags_seen or kept >= MAX_TAGS:
            return ""
        tags_seen.append(low); kept += 1
        return t

    out = re.sub(r"#\w+", keep, text)
    out = re.sub(r"[ \t]+\n", "\n", out)
    out = re.sub(r"[ \t]{2,}", " ", out).strip()
    if "Fan-made" not in out:
        # 해시태그 줄 앞에 면책 문구 넣기
        lines = out.split("\n")
        idx = next((i for i in range(len(lines) - 1, -1, -1) if lines[i].strip().startswith("#")), len(lines))
        lines[idx:idx] = [DISCLAIMER, ""]
        out = "\n".join(lines).strip()
    first = out.split("\n", 1)[0]
    if len(first) > 125:
        print(f"참고: 첫 줄이 {len(first)}자예요 (125자 안에 핵심 키워드가 오면 좋아요)")
    print(f"해시태그 {kept}개 사용")
    return out


def candidates(caption):
    """캡션의 '1️⃣ 이름' 부분에서 후보 이름 뽑기."""
    names = {}
    parts = re.split(r"([1-4])️⃣", caption)
    for i in range(1, len(parts) - 1, 2):
        chunk = parts[i + 1].split("\n")[0]
        name = re.split(r"\s+[–-]\s+|\s{2,}", chunk.strip())[0].strip()
        if name and parts[i] not in names:
            names[parts[i]] = name
    return names


def headline(caption):
    first = caption.split("\n", 1)[0]
    return re.split(r"\s+in 4 panels", first)[0].strip()


# ---------- 지난 편 투표 집계 ----------
def last_posted(exclude):
    best = None
    for f in glob.glob("posts/*/posted.txt"):
        folder = os.path.dirname(f)
        if folder == exclude:
            continue
        line = open(f, encoding="utf-8").read().split("\n")[0].split()
        if len(line) < 3:
            continue
        stamp = " ".join(line[:2])
        media_id = next((x[3:] for x in line if x.startswith("id=")), None)
        if media_id and (best is None or stamp > best[0]):
            best = (stamp, folder, media_id)
    return best


def tally(media_id):
    votes = collections.Counter()
    voters = set()
    after = None
    for _ in range(10):
        params = dict(fields="text,username", limit=50)
        if after:
            params["after"] = after
        res = call("GET", f"{media_id}/comments", **params)
        for c in res.get("data", []):
            who = c.get("username") or c.get("id")
            m = re.search(r"(?<![0-9])([1-4])(?![0-9])", c.get("text", ""))
            if m and who not in voters:
                voters.add(who); votes[m.group(1)] += 1
        after = res.get("paging", {}).get("cursors", {}).get("after")
        if not res.get("paging", {}).get("next"):
            break
    return votes


def first_comment(folder, caption):
    lines = []
    prev = last_posted(folder)
    if prev:
        _, pfolder, pid = prev
        try:
            votes = tally(pid)
            pcap = open(f"{pfolder}/caption.txt", encoding="utf-8").read()
            names = candidates(pcap)
            total = sum(votes.values())
            if total >= 3:
                n, k = votes.most_common(1)[0]
                lines.append(f"📊 Last comic ({headline(pcap)}): you voted {names.get(n, '#' + n)} as MOTM with {round(k * 100 / total)}% of {total} votes.")
            else:
                print("지난 편 투표 수가 적어서 결과 공개는 건너뜀:", total)
        except Exception as e:
            print("투표 집계 실패(건너뜀):", e)
    lines.append("👇 Your MOTM? Just comment the number. We'll reveal the winner in the next comic.")
    return "\n\n".join(lines)


# ---------- 게시 ----------
def alt_texts(folder, imgs, caption):
    p = f"{folder}/alt.txt"
    if os.path.exists(p):
        alts = [l.strip() for l in open(p, encoding="utf-8").read().split("\n") if l.strip()]
    else:
        h = headline(caption)
        alts = [f"Four-panel chibi football comic: {h}.", f"Man of the Match vote card: {h}."]
    return [(alts[i] if i < len(alts) else alts[-1])[:1000] for i in range(len(imgs))]


def make_child(uid, image_url, alt):
    try:
        return call("POST", f"{uid}/media", image_url=image_url, is_carousel_item="true", alt_text=alt)["id"]
    except ApiError:
        print("대체 텍스트 없이 다시 시도")
        return call("POST", f"{uid}/media", image_url=image_url, is_carousel_item="true")["id"]


def make_parent(uid, collab, **params):
    if collab:
        try:
            return call("POST", f"{uid}/media", collaborators=json.dumps(collab), **params)["id"]
        except ApiError:
            print("공동 게시 초대 없이 다시 시도")
    return call("POST", f"{uid}/media", **params)["id"]


def share_story(uid, image_url):
    try:
        c = call("POST", f"{uid}/media", image_url=image_url, media_type="STORIES")["id"]
        wait_ready(c)
        call("POST", f"{uid}/media_publish", creation_id=c)
        print("스토리 공유 완료")
        return True
    except Exception as e:
        print("스토리 공유 건너뜀:", str(e)[:200])
        return False


def publish(folder):
    imgs = sorted(glob.glob(f"{folder}/*.jpg"), key=lambda p: int(os.path.basename(p).split(".")[0]))
    caption = clean_caption(open(f"{folder}/caption.txt", encoding="utf-8").read())
    collab = []
    if os.path.exists(f"{folder}/collab.txt"):
        collab = [l.strip().lstrip("@") for l in open(f"{folder}/collab.txt", encoding="utf-8") if l.strip()][:3]
    me = call("GET", "me", fields="user_id,username")
    uid = me["user_id"]; print("계정:", me.get("username"))
    url = lambda p: f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{p}"
    alts = alt_texts(folder, imgs, caption)

    if len(imgs) == 1:
        c = make_parent(uid, collab, image_url=url(imgs[0]), caption=caption, is_ai_generated="true", alt_text=alts[0])
    else:
        kids = []
        for p, a in zip(imgs, alts):
            k = make_child(uid, url(p), a)
            wait_ready(k); kids.append(k)
        c = make_parent(uid, collab, media_type="CAROUSEL", children=",".join(kids), caption=caption, is_ai_generated="true")
    wait_ready(c)
    res = call("POST", f"{uid}/media_publish", creation_id=c)
    mid = res["id"]
    link = call("GET", mid, fields="permalink").get("permalink", "")
    open(f"{folder}/posted.txt", "w").write(f"{datetime.datetime.now(KST):%Y-%m-%d %H:%M} {link} id={mid}\n")
    print("게시 완료:", link)

    # 게시 후 자동 작업 (실패해도 게시는 이미 끝남)
    notes = []
    try:
        msg = first_comment(folder, caption)
        call("POST", f"{mid}/comments", message=msg)
        notes.append("첫 댓글 완료")
    except Exception as e:
        notes.append(f"첫 댓글 실패: {str(e)[:120]}")
    notes.append("스토리 공유 완료" if share_story(uid, url(imgs[0])) else "스토리 공유 건너뜀")
    with open(f"{folder}/posted.txt", "a") as f:
        f.write("# " + " / ".join(notes) + "\n")
    print(" / ".join(notes))


now = datetime.datetime.now(KST)
done = 0
for folder in sorted(glob.glob("posts/*/")):
    folder = folder.rstrip("/")
    if os.path.exists(f"{folder}/posted.txt"):
        continue
    if ONLY and os.path.basename(folder) != ONLY:
        continue
    if not ONLY and os.path.exists(f"{folder}/post_at.txt"):
        t = datetime.datetime.strptime(open(f"{folder}/post_at.txt").read().strip(), "%Y-%m-%d %H:%M").replace(tzinfo=KST)
        if t > now:
            print("대기:", folder, t); continue
    elif not ONLY:
        continue  # 시간 없는 폴더는 직접 실행할 때만
    publish(folder); done += 1
print("이번 실행 게시 수:", done)
