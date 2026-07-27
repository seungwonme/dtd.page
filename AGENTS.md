# dtd.page

이 저장소는 `@dtd.page`의 책 문구 카드뉴스를 만들고 공식 Instagram Graph API로 발행한다.

## 고정 형식

- 한 게시물은 표지 1장과 문구 3-5장으로 구성한다.
- 원문은 `$DTD_PDF_ROOT` 아래 PDF만 사용한다. 기본값은 `$HOME/Library/Mobile Documents/com~apple~CloudDocs/PDF`다.
- 문구를 지어내거나 의역해서 직접 인용처럼 쓰지 않는다. 책 제목, 저자, PDF 상대 경로, 가능하면 쪽수를 남긴다.
- 사용자가 고른 문구가 아니면 `approved`를 `false`로 두고 초안 이미지만 만든다.
- 공개 발행은 `approved: true`인 콘텐츠에만 허용한다.

## Discord에서 처리하는 순서

1. 사용자가 책과 문구 3-5개를 주면 `content/YYYY-MM-DD-<slug>.json`을 만든다.
2. `./scripts/dtd.sh render <content.json>`으로 1080x1350 PNG를 생성한다.
3. 생성된 이미지를 사용자에게 보여주고 수정 요청을 반영한다.
4. 사용자가 발행을 승인하면 JSON의 `approved`를 `true`로 바꾼다.
5. `agents-env run INSTAGRAM_ACCESS_TOKEN INSTAGRAM_USER_ID -- ./scripts/dtd.sh release <content.json> --publish`를 실행한다.

사용자가 "자동으로 골라줘"라고 해도 초안까지만 만든다. 사용자의 취향을 추정한 결과를 승인된 직접 인용으로 취급하지 않는다.

## 명령

```bash
uv sync
./scripts/dtd.sh extract '190-Personal-Development/.../book.pdf' --pages 1-30
./scripts/dtd.sh render content/example.json
./scripts/dtd.sh release content/example.json
uv run pytest -q
```

`release`는 기본 dry-run이다. `--publish`를 붙이면 정확한 콘텐츠/이미지/상태 파일만 커밋하고 push한 뒤, GitHub Pages URL이 열릴 때까지 기다리고 carousel을 발행한다. `state/<post-id>.json`이 이미 있으면 중복 발행을 막는다.

## 보안과 운영

- 토큰을 파일, Git, 명령 출력에 남기지 않는다. 시크릿은 `agents-env`로만 주입한다.
- 발행 전 `@dtd.page`가 Instagram Professional 계정이고 Meta 앱 권한이 유효한지 확인한다.
- 브라우저 비공식 자동 게시를 우회 수단으로 쓰지 않는다.
- PDF 원문과 추출 텍스트는 커밋하지 않는다. `.work/`는 로컬 임시 작업 전용이다.
- 발행 실패 뒤 `state/*.json`이 `pending`이면 재실행하지 말고 Instagram 게시물 존재 여부부터 확인한다.
