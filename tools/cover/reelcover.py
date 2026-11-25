"""KickOff Comics 릴스 표지 — 하나뿐인 공식 틀 (2026-11-25 현승님 "하나로 통일").
모든 릴스 cover.jpg는 이 스크립트로만 만든다. 영상 프레임을 그대로 표지로 쓰지 않는다.

틀(고정, 바꾸지 말 것):
  - 1080x1920. 장면 그림(글자 없는 원본장면)을 가로 꽉 채워 아래쪽에 붙이고, 남는 위쪽은 같은 그림을 흐리게.
  - 위쪽 어두운 둥근 상자(x 120~960, y 250부터) 안에 2줄: 1줄 흰색(상황), 2줄 노랑 #FFD400(질문·반전). Bangers + 숫자는 Nunito Black, 검은 테두리 8.
  - 아래쪽 계정 배지 "@KICK_OFF_COMICS" (라벤더 #AEBCFE 알약, 남색 글씨), 가운데, y 1560 근처.
  - 글자·배지는 모두 인스타 그리드(가운데 3:4 = y 240~1680)와 아이폰 안전 영역(x 140~940) 안.
사용: python3 reelcover.py <장면.png|jpg> "LINE 1" "LINE 2" <출력.jpg> [fy=0.35]
  fy = 장면이 화면보다 길 때 세로 어느 쪽을 보일지(0=위, 1=아래). 얼굴·공이 상자·배지에 가리지 않게 조정."""
import sys, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
F = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
W, H = 1080, 1920
WHITE, YELLOW, BLACK = (255, 255, 255), (255, 212, 0), (0, 0, 0)
BADGE_BG, BADGE_FG = (174, 188, 254), (16, 22, 60)
def bang(s): return ImageFont.truetype(f"{F}/Bangers.ttf", s)
def nun(s):
    f = ImageFont.truetype(f"{F}/Nunito.ttf", s); f.set_variation_by_name(b"Black"); return f
def mlen(d, t, bf, nf): return sum(d.textlength(c, font=(nf if c.isdigit() else bf)) for c in t)
def mdraw(d, x, y, t, bf, nf, **kw):
    for c in t:
        f = nf if c.isdigit() else bf; d.text((x, y), c, font=f, anchor="ls", **kw); x += d.textlength(c, font=f)
def make(scene, l1, l2, out, fy=0.35):
    src = Image.open(scene).convert("RGB")
    s = W / src.width; sc = src.resize((W, round(src.height * s)), Image.LANCZOS)
    bg = src.resize((round(src.width * H / src.height), H), Image.LANCZOS)
    if bg.width < W: bg = bg.resize((W, round(bg.height * W / bg.width)), Image.LANCZOS)
    bx = (bg.width - W) // 2; bg = bg.crop((bx, 0, bx + W, H)).filter(ImageFilter.GaussianBlur(18))
    im = ImageEnhance.Brightness(bg).enhance(0.6)
    if sc.height > H:
        off = int((sc.height - H) * fy); sc = sc.crop((0, off, W, off + H)); y0 = 0
    else:
        y0 = H - sc.height
    mask = Image.new("L", sc.size, 255); md = ImageDraw.Draw(mask)
    if y0 > 0:
        for k in range(60): md.line((0, k, W, k), fill=int(255 * k / 60))
    im.paste(sc, (0, y0), mask); im = im.convert("RGBA")
    d0 = ImageDraw.Draw(im)
    lines = [(l1.upper(), WHITE), (l2.upper(), YELLOW)]
    sizes = []
    for t, _ in lines:
        sz = 140
        while mlen(d0, t, bang(sz), nun(int(sz * .9))) > 780 and sz > 60: sz -= 4
        sizes.append(sz)
    top, gap = 250, 18; h = sum(sizes) + gap + 70
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    od.rounded_rectangle((120, top, W - 120, top + h), radius=34, fill=(10, 12, 24, 165))
    # 계정 배지
    bt = "@KICK_OFF_COMICS"; bf = nun(40); bw = od.textlength(bt, font=bf) + 64; bh = 72
    bx0 = (W - bw) / 2; by0 = 1540
    od.rounded_rectangle((bx0, by0, bx0 + bw, by0 + bh), radius=bh // 2, fill=BADGE_BG + (240,), outline=(255, 255, 255, 255), width=4)
    im.alpha_composite(ov); d = ImageDraw.Draw(im)
    d.text((W / 2, by0 + bh / 2 + 2), bt, font=bf, fill=BADGE_FG, anchor="mm")
    yb = top + 35
    for (t, col), sz in zip(lines, sizes):
        b, n = bang(sz), nun(int(sz * .9)); yb += sz
        w = mlen(d, t, b, n); mdraw(d, (W - w) / 2, yb - int(sz * 0.12), t, b, n, fill=col, stroke_width=8, stroke_fill=BLACK)
        yb += gap
    im.convert("RGB").save(out, quality=93)
if __name__ == "__main__":
    a = sys.argv[1:]; make(a[0], a[1], a[2], a[3], float(a[4]) if len(a) > 4 else 0.35)
