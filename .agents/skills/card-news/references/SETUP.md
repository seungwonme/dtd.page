# 설정과 이전

## 설정 위치

비민감 환경값의 정본은 `${XDG_CONFIG_HOME:-$HOME/.config}/card-news/config.env`다. 초기화는 직접 편집 대신 다음 명령을 실행한다.

```bash
.agents/skills/card-news/scripts/card-news.sh setup <project-root>
```

`setup`은 설정이 없을 때만 만들고 권한을 `600`으로 제한한다. 프로젝트의 기존 `.env.local` 또는 `.env.example`에서 허용된 공개 값만 옮기며 토큰, 비밀번호, secret, key 이름은 복사하지 않는다.

## 환경값

- `CARD_NEWS_PROJECT_ROOT`: `dtd.page` 저장소 절대 경로
- `CARD_NEWS_DEFAULT_TEMPLATE`: 새 콘텐츠에 기록할 기본 템플릿
- `DTD_PDF_ROOT`: PDF 라이브러리 루트
- `DTD_PUBLIC_BASE_URL`: Meta가 이미지를 읽을 공개 URL
- `DTD_INSTAGRAM_USERNAME`: 발행 대상 계정명
- `DTD_DISPLAY_NAME`: 서명형 표시 이름
- `INSTAGRAM_USER_ID`: 공개 Instagram 사용자 ID
- `INSTAGRAM_GRAPH_VERSION`: Graph API 버전
- `DTD_FONT_PATH`: Pretendard 기본 위치가 다를 때만 지정
- `DTD_PROFILE_IMAGE`: 프로젝트 기본 프로필을 바꿀 때만 지정

`INSTAGRAM_ACCESS_TOKEN`은 이 파일에 넣지 않는다. `agents-env`가 유일한 정본이다.

## 진단과 이전

```bash
.agents/skills/card-news/scripts/card-news.sh doctor
.agents/skills/card-news/scripts/card-news.sh doctor --auth
```

다른 컴퓨터에서는 저장소를 준비하고 스킬을 설치한 뒤 `setup`을 다시 실행한다. 마지막으로 사람이 그 컴퓨터의 `agents-env`에 토큰을 등록하고 `doctor --auth`로 읽기 전용 검증한다.
