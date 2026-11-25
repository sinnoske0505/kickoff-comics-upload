"""KickOff Comics reel builder (힉스필드 그림 1장 구조, 11/25).
usage: python3 build.py cfg.json   (cfg 폴더 기준 상대경로)
cfg = {"font":"Bangers.ttf","music":"music.mp3","out":"reel.mp4","hook":["LINE1","LINE2"],
       "cuts":[{"clip":"clips/c1.mp4","wav":"n1.wav","disp":"TEXT|CHUNK...","goal":0.4,"score":"1-0",
                "board":["MCI 0-0 NAP","MCI 0-1 NAP","55'"], "ss":0, "slow":1.0, "dur":null}, ...]}
- 첫 컷은 hook 두 줄(흰/노랑) 표시, disp 없음.
- clip 앞부분 ss초부터, slow배 느리게(setpts), dur초만 사용(없으면 끝까지 + 마지막 프레임 정지).
- goal 초에 펀치인·흔들림·흰 플래시·노랑 점수 팝, board는 위쪽 고정 스코어보드(goal 전/후 문구 + 분).
"""
import subprocess, os, json, sys
cfgp = os.path.abspath(sys.argv[1]); os.chdir(os.path.dirname(cfgp)); C = json.load(open(cfgp))
FONT = C.get('font', 'Bangers.ttf'); MUSIC = C.get('music', 'music.mp3'); OUT = C.get('out', 'reel.mp4')
W, H = 1080, 1920; GAP, XF = 0.35, 0.25; cuts = C['cuts']; N = len(cuts)
def dur(f): return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',f]))
def esc(s): return s.replace('\\','\\\\').replace("'","’").replace(':','\\:').replace(',','\\,').replace('%','\\%')
os.makedirs('seg', exist_ok=True); segs = []
for i, c in enumerate(cuts):
    n = i + 1; nd = dur(c['wav']); L = max(nd + GAP, c.get('min', 2.6)) + (1.0 if n == N else 0); LV = L + (XF if n < N else 0)
    pre = []
    if c.get('ss'): pre.append(f"trim=start={c['ss']}")
    if c.get('dur'): pre.append(f"trim=duration={c['dur']}" if not c.get('ss') else f"trim=start={c['ss']}:duration={c['dur']}")
    if c.get('ss') and c.get('dur'): pre = [f"trim=start={c['ss']}:duration={c['dur']}"]
    vf = pre + [f"setpts={c.get('slow',1.0)}*(PTS-STARTPTS)", "tpad=stop_mode=clone:stop_duration=10",
          f"scale={W}:{H}:force_original_aspect_ratio=increase", f"crop={W}:{H}", "fps=30"]
    g = c.get('goal')
    if g is not None:
        vf.append(f"scale=w='iw*(1+0.06*between(t\\,{g}\\,{g+0.45}))':h=-2:eval=frame")
        vf.append(f"crop={W}:{H}:x='(iw-{W})/2+18*sin(t*90)*between(t\\,{g}\\,{g+0.45})':y='(ih-{H})/2+14*cos(t*77)*between(t\\,{g}\\,{g+0.45})'")
        vf.append(f"drawbox=x=0:y=0:w=iw:h=ih:color=white@0.7:t=fill:enable='between(t\\,{g}\\,{g+0.07})'")
        if c.get('score'):
            pop = f"118+60*max(0\\,1-(t-{g})/0.18)"
            vf.append(f"drawtext=fontfile={FONT}:text='{esc(c['score'])}':fontsize='{pop}':fontcolor=0xFFD400:borderw=8:bordercolor=black:x=(w-tw)/2:y=330:enable='between(t\\,{g}\\,{g+1.2})'")
    if c.get('board'):
        b0, b1, mn = c['board']
        vf.append("drawbox=x=250:y=170:w=580:h=100:color=0x0B1A3A@0.88:t=fill")
        vf.append("drawbox=x=250:y=262:w=580:h=8:color=0xFFD400@1:t=fill")
        sw = g if g is not None else 99
        for txt, en in ((b0, f"lt(t\\,{sw})"), (b1, f"gte(t\\,{sw})")):
            if txt: vf.append(f"drawtext=fontfile={FONT}:text='{esc(txt)}':fontsize=64:fontcolor=white:x=(w-tw)/2-40:y=190:enable='{en}'")
        if mn: vf.append(f"drawtext=fontfile={FONT}:text='{esc(mn)}':fontsize=54:fontcolor=0xFFD400:x=725:y=198")
    if n == 1:
        for k, (txt, y) in enumerate(zip(C['hook'], (300, 420))):
            fs = f"100+40*max(0\\,1-(t-{0.15+k*1.2})/0.15)"
            vf.append(f"drawtext=fontfile={FONT}:text='{esc(txt)}':fontsize='{fs}':fontcolor={'white' if k==0 else '0xFFD400'}:borderw=9:bordercolor=black:x=(w-tw)/2:y={y}:enable='gte(t\\,{0.15+k*1.2})'")
    elif c.get('disp'):
        d = c['disp']
        if '|' in d: chunks = [x.split() for x in d.split('|')]
        else:
            chunks, cur = [], []
            for w in d.split():
                cur.append(w)
                if len(cur) == 3 or w.endswith(('.', ',', '!', '?', '...')): chunks.append(cur); cur = []
            if cur: chunks.append(cur)
        tot = sum(len(' '.join(x)) for x in chunks); t0 = 0.05
        for x in chunks:
            txt = ' '.join(x); dd = nd * len(txt) / tot; last = (n == N and x is chunks[-1])
            fs = f"90+34*max(0\\,1-(t-{t0:.2f})/0.12)"
            vf.append(f"drawtext=fontfile={FONT}:text='{esc(txt)}':fontsize='{fs}':fontcolor=white:borderw=8:bordercolor=black:x=(w-tw)/2:y=1330:enable='between(t\\,{t0:.2f}\\,{t0+dd+(1.2 if last else 0):.2f})'")
            t0 += dd
    out = f'seg/s{n}.mp4'
    subprocess.run(['ffmpeg','-nostdin','-y','-loglevel','error','-i',c['clip'],'-i',c['wav'],'-filter_complex',
        f"[0:v]{','.join(vf)}[v];[1:a]aresample=48000,apad=whole_dur={L}[a]",'-map','[v]','-map','[a]','-t',f'{LV}',
        '-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-b:a','160k',out], check=True)
    segs.append((out, L)); print(out, round(L, 2))
ins = []
for p, _ in segs: ins += ['-i', p]
fc = []; prev = '[0:v]'; acc = 0.0
for k in range(1, len(segs)):
    acc += segs[k-1][1]; fc.append(f"{prev}[{k}:v]xfade=transition=slideleft:duration={XF}:offset={acc:.3f}[x{k}]"); prev = f'[x{k}]'
aud = ''.join(f"[{k}:a]atrim=0:{segs[k][1]:.3f},asetpts=PTS-STARTPTS[a{k}];" for k in range(len(segs)))
fc.append(aud + ''.join(f'[a{k}]' for k in range(len(segs))) + f"concat=n={len(segs)}:v=0:a=1[aa]")
subprocess.run(['ffmpeg','-nostdin','-y','-loglevel','error',*ins,'-filter_complex',';'.join(fc),'-map',prev,'-map','[aa]',
    '-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','seg/joined.mp4'], check=True)
D = dur('seg/joined.mp4')
subprocess.run(['ffmpeg','-nostdin','-y','-loglevel','error','-i','seg/joined.mp4','-i',MUSIC,'-filter_complex',
    f"[1:a]volume=0.12,afade=t=out:st={D-1.5}:d=1.5[m];[0:a][m]amix=inputs=2:duration=first:normalize=0[a]",
    '-map','0:v','-map','[a]','-c:v','libx264','-crf','23','-maxrate','4M','-bufsize','8M','-pix_fmt','yuv420p',
    '-c:a','aac','-b:a','160k','-movflags','+faststart',OUT], check=True)
print('done', round(D, 2))
