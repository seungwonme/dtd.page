# 책 문구 카드뉴스 워크플로

## 콘텐츠 계약

콘텐츠 JSON은 다음 골격을 사용한다.

```json
{
  "date": "YYYY-MM-DD",
  "slug": "book-slug",
  "template": "minimal",
  "book": {
    "title": "책 제목",
    "author": "저자",
    "source_pdf": "PDF 루트 기준 상대 경로"
  },
  "quotes": [
    {
      "text": "PDF에서 대조한 직접 인용",
      "chapter": "Chapter 01 / 실제 목차명",
      "page": "검증용 PDF 내부 쪽수"
    }
  ],
  "caption": "게시물 캡션",
  "approved": false
}
```

- 문구는 3-5개다.
- `page`는 검증 기록이며 이미지에는 표시하지 않는다.
- `minimal` 카드는 `chapter`를 표시한다. `signature`는 검증 기록에만 보존하고 카드에는 푸터를 표시하지 않는다.
- `signature`는 책 고유성, 문맥 독립성, 1-2줄 조건을 모두 통과한 문구가 3개 이상일 때만 선택한다. 부족하면 `minimal`로 전환한다.
- 표지는 PDF 첫 페이지에서 흰 여백과 뷰어 진행 표시를 제거한 실제 책 표지를 사용한다.
- 사용자가 문구를 직접 골랐더라도 이미지 검수 전에는 `approved: false`를 유지한다.

## 실행 순서

```bash
.agents/skills/card-news/scripts/card-news.sh extract <pdf-relative-path> --pages <start-end>
.agents/skills/card-news/scripts/card-news.sh compare <content.json>
.agents/skills/card-news/scripts/card-news.sh render <content.json>
.agents/skills/card-news/scripts/card-news.sh dry-run <content.json>
```

`dry-run`은 공개 URL과 캡션 계획만 확인한다. 실제 발행은 사용자 승인과 `approved: true`를 모두 확인한 뒤 다음 명령을 사용한다.

```bash
.agents/skills/card-news/scripts/card-news.sh publish <content.json>
```

발행 실패 뒤 `state/*.json`이 `pending`이면 재실행하지 않는다. Instagram 게시물 존재 여부를 먼저 확인해 중복 발행을 막는다.
