# 인스타 점검 도구 (instagram-agent-skill, MIT, Jake Schincariol)

필요한 것만 가져옴. 모두 내 컴퓨터에서 글만 보고 점수를 냄(인스타 접속 없음).

| 도구 | 쓰는 때 | 명령 |
|---|---|---|
| caption.py | 캡션 올리기 전: 피드에 보이는 첫 125자, 해시태그, 요청 1개 | `python3 tools/ig/caption.py posts/<폴더>/caption.txt` |
| detect.py | 영어 캡션의 AI 티 점수(70점 이상 목표) | `python3 tools/ig/detect.py posts/<폴더>/caption.txt` |
| humanize.py | AI 티 나는 표현 찾아 고칠 곳 표시 | `python3 tools/ig/humanize.py <파일>` |
| hookscore.py | 1번 컷 문구·릴스 첫 문구 훅 점수 | `echo "문구" \| python3 tools/ig/hookscore.py -` |
| swipe.py | 월간 바이럴 조사 표(계정·팔로워·중앙값·조회·훅) 순위 | `python3 tools/ig/swipe.py captured.tsv --out swipe.md` |

주간 성과 분석은 `scripts/insights.py`(Actions → 성과 분석, 매주 화 18:37 KST 자동).
