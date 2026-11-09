---
argument-hint: "[book-or-content]"
name: card-news
description: "Use for: Turn verified book-PDF quotations into Instagram carousels with a cover, template comparisons, dtd.page drafts, previews, user review, and approved official-API publishing. Not for non-book marketing carousels or unverified quotes."
---

# Card News

책 원문과 사용자 승인을 보존하면서 카드뉴스 초안부터 발행까지 처리한다. 실행은 `scripts/card-news.sh`에 맡기고 템플릿 구현은 설정된 프로젝트의 레지스트리를 정본으로 사용한다.

## 필수 안전선

- 원문은 설정된 PDF 루트 아래 파일만 사용한다.
- 직접 인용은 PDF에서 문구, 실제 챕터명, 검증용 PDF 쪽수를 확인한다.
- 자동으로 고른 문구와 새 초안은 `approved: false`로 저장한다.
- 사용자가 최종 이미지를 보고 발행을 명시적으로 승인한 뒤에만 `approved: true`로 바꾼다.
- 토큰은 `agents-env`로만 주입하고 파일이나 출력에 남기지 않는다.
- 공개 발행은 공식 Instagram Graph API 경로만 사용한다.

## 작업 라우팅

| 작업 | 먼저 읽을 것 |
|---|---|
| 최초 설정, 환경 진단, 다른 컴퓨터 이전 | [references/SETUP.md](references/SETUP.md) |
| PDF 추출, 콘텐츠 작성, 검수, 발행 | [references/workflow.md](references/workflow.md) |
| 템플릿 선택, 비교, 새 유형 추가 | [references/templates.md](references/templates.md) |

## 기본 워크플로

1. `scripts/card-news.sh doctor`로 프로젝트, PDF, 글꼴, 프로필을 확인한다.
2. 사용자가 지정한 PDF 범위에서 문구 3-5개와 실제 챕터명을 검증한다.
3. 콘텐츠 JSON에 명시적 `template`과 `approved: false`를 기록한다.
4. 선택이 필요하면 `compare`, 확정됐으면 `render`를 실행해 이미지를 보여준다.
5. 수정 요청을 반영하고 다시 렌더한다.
6. 명시적 발행 승인을 받은 뒤에만 승인 상태를 바꾸고 `publish`를 실행한다.

## 실행 표면

프로젝트 루트(`dtd.page`)에서 실행한다.

```bash
.agents/skills/card-news/scripts/card-news.sh setup <project-root>
.agents/skills/card-news/scripts/card-news.sh templates
.agents/skills/card-news/scripts/card-news.sh compare <content.json>
.agents/skills/card-news/scripts/card-news.sh render <content.json>
.agents/skills/card-news/scripts/card-news.sh publish <content.json>
```

작업 완료 시 사용한 PDF 상대 경로, 템플릿, 생성 이미지 경로, 승인 여부를 보고한다. 발행하지 않았다면 그 사실도 명시한다.
