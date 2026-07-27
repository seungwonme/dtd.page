# dtd.page

책에서 고른 문구 3-5개를 표지 포함 Instagram carousel로 만드는 자동화 작업환경입니다.

```bash
uv sync
./scripts/dtd.sh render content/example.json
./scripts/dtd.sh release content/example.json
```

`release`는 기본적으로 dry-run입니다. 실제 발행은 콘텐츠 JSON의 `approved`를 `true`로 바꾼 뒤 실행합니다.

```bash
agents-env run INSTAGRAM_ACCESS_TOKEN INSTAGRAM_USER_ID -- \
  ./scripts/dtd.sh release content/2026-07-27-example.json --publish
```

## 콘텐츠 형식

```json
{
  "date": "2026-07-27",
  "slug": "book-slug",
  "book": {
    "title": "책 제목",
    "author": "저자",
    "source_pdf": "190-Personal-Development/.../book.pdf"
  },
  "quotes": [
    {"text": "마음에 든 문장", "page": "42"},
    {"text": "두 번째 문장", "page": "87"},
    {"text": "세 번째 문장", "page": "121"}
  ],
  "caption": "오늘 마음에 머문 문장들.",
  "approved": false
}
```

이미지는 `docs/posts/<date>-<slug>/`에 생성되고 GitHub Pages에서 Meta가 읽을 수 있는 공개 URL로 제공됩니다. PDF와 추출 원문은 저장소에 올라가지 않습니다.

## 준비 조건

- `@dtd.page`를 Instagram Professional 계정으로 전환
- Facebook Page 연결과 Meta 앱의 content publishing 권한
- `agents-env` 전역 저장소에 `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_USER_ID` 등록
- 필요하면 `INSTAGRAM_GRAPH_VERSION`을 등록해 기본 `v23.0`을 덮어쓰기
