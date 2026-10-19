# 킥오프코믹스 인스타 자동 업로드

- `posts/<폴더>/` 에 `1.jpg, 2.jpg …` + `caption.txt` (+ 예약하려면 `post_at.txt` = `2026-10-22 19:00`, 한국시간)
- 매시 7분에 시간이 된 게시물을 올리고 `posted.txt` 에 링크를 남깁니다.
- 바로 올리기: Actions → 인스타 업로드 → Run workflow → 폴더 이름 입력
- 필요한 비밀값: `IG_TOKEN` (Settings → Secrets and variables → Actions)
- 토큰은 매월 1일·15일 자동 연장됩니다.
