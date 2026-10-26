#!/bin/bash
# 릴스 컷 영상을 60fps로 모션 보간 (2026-10-26 현승님 60fps 확정)
# 사용: bash tools/interp60.sh <입력 폴더(01.mp4.. / 01_full.mp4)> <출력 폴더> [슬로 지정 "04:2.7:2.4" ...]
#  - 기본: 각 컷 앞 7.5초를 60fps로 보간
#  - 슬로 지정: "<컷>:<앞 몇 초>:<몇 배>" → 그 구간을 늘린 뒤 보간 (뚝뚝 끊김 방지)
#  - 클라우드 컨테이너에서 실행(맥미니 VM은 호출당 180초 제한). 5컷 ≈ 7~8분.
IN=$1; OUT=$2; shift 2; mkdir -p "$OUT"
declare -A SL; for s in "$@"; do k=${s%%:*}; SL[$k]=${s#*:}; done
MI="minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1"
for f in "$IN"/[0-9][0-9].mp4 "$IN"/[0-9][0-9]_full.mp4; do [ -f "$f" ] || continue
  k=$(basename "$f" .mp4); k=${k%_full}; [ -f "$OUT/$k.mp4" ] && continue
  src="$IN/$k.mp4"; [ -f "$IN/${k}_full.mp4" ] && src="$IN/${k}_full.mp4"
  if [ -n "${SL[$k]}" ]; then t=${SL[$k]%%:*}; x=${SL[$k]#*:}
    ffmpeg -v error -y -t $t -i "$src" -vf "setpts=${x}*PTS,$MI" -an -c:v libx264 -crf 16 -preset veryfast "$OUT/$k.mp4" &
  else
    ffmpeg -v error -y -t 7.5 -i "$src" -vf "$MI" -an -c:v libx264 -crf 16 -preset veryfast "$OUT/$k.mp4" &
  fi
done; wait; ls -la "$OUT"
