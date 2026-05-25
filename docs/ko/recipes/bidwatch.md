# bidwatch — 입찰공고 파싱 + Vision 라벨링 + 자체 DB 저장 패턴

> **독자:** bidwatch 의 백엔드 개발자
> **대상 라이브러리 버전:** `korean-doc-parser` v0.5.0+

이 문서는 bidwatch 가 `korean-doc-parser` 를 호출 라이브러리로 사용해서
입찰공고 (HWP / PDF / HWPX 위주) 를 본인 PostgreSQL 에 박는 권장 패턴을
보여줍니다. 라이브러리는 **데이터 객체 + 알고리즘만** 반환, 저장은 100%
bidwatch 책임입니다 (worklog/019 의 결정).

---

## 1. 설치

```bash
pip install "git+https://github.com/Brad0329/korean-doc-parser.git@v0.5.0#subdirectory=packages/core[vision]"
pip install "git+https://github.com/Brad0329/korean-doc-parser.git@v0.5.0#subdirectory=packages/hwp"
```

- `[vision]` extras = Anthropic SDK 포함 (Claude Vision 호출용)
- HWP 격리 패키지는 AGPL-3.0+ — bidwatch 가 GPL/AGPL 영향 받는지 사전 확인

---

## 2. 환경 설정

```bash
# .env (bidwatch 의 dotenv 또는 시스템 환경변수)
ANTHROPIC_API_KEY=sk-ant-xxx
```

`korean-doc-parser` 의 CLI 는 `.env` 자동 로드 (Python API 는 호출자가
명시적으로 환경변수 셋업).

---

## 3. 핵심 사용 패턴

```python
import korean_doc_parser_hwp  # noqa: F401  ─ HWP 등록 (HWP 처리 시만)
from pathlib import Path

from korean_doc_parser import extract, ParseError
from korean_doc_parser.pipeline import (
    compute_doc_id,
    weighted_confidence,
    detect_caption_regex,
)
from korean_doc_parser.vision import VisionClient
from korean_doc_parser.vision.cache import VisionCache


def ingest_notice(notice_path: Path, bidwatch_db) -> str:
    """입찰공고 1건 → bidwatch DB 에 저장. 반환: doc_id (sha256)."""

    # 1) 문서 파싱
    try:
        result = extract(notice_path)
    except ParseError as e:
        bidwatch_db.errors.insert(path=str(notice_path), error=str(e))
        raise

    # 2) doc_id 계산 — bidwatch 의 primary key
    doc_id = compute_doc_id(notice_path)

    # 3) 문서 메타 저장 (bidwatch 자체 schema)
    bidwatch_db.documents.upsert(
        doc_id=doc_id,
        path=str(notice_path),
        format=result.metadata.format,
        title=result.metadata.title,
        markdown=result.markdown,
        page_count=result.metadata.page_count,
        ingested_at="now()",
    )

    # 4) 표 저장 — list[list[str]] 그대로 또는 jsonb
    for idx, table in enumerate(result.tables):
        bidwatch_db.tables.insert(
            doc_id=doc_id,
            order=idx,
            page_no=table.page_no,
            rows=table.rows,
        )

    # 5) 이미지 + Vision 라벨링
    vision = VisionClient(
        # default = claude-haiku-4-5 (worklog/014 의 1/10 비용)
        cache=VisionCache("/var/lib/bidwatch/kdp-cache.db"),
    )
    seen_sha = set()  # 같은 sha256 중복 제거 (PPTX/PDF 의 반복 이미지)
    for img in result.images:
        # 5-1. 작은 비트맵 (로고 등) 은 Vision 호출 안 함
        if img.width < 100 or img.height < 100:
            continue
        # 5-2. 중복은 한 번만 라벨, 여러 페이지로 매핑
        if img.sha256 not in seen_sha:
            try:
                vr = vision.label(img.file_path)
            except Exception as e:
                bidwatch_db.errors.insert(doc_id=doc_id, sha=img.sha256, error=str(e))
                continue
            seen_sha.add(img.sha256)

            # 5-3. 1차 caption (engine-side, 결정론적)
            text_window = img.text_before + "\n" + img.text_after
            regex_cap, regex_score = detect_caption_regex(text_window)

            # 5-4. 3중 가중 — bidwatch 가 임계값 결정 (예: 0.7)
            final_conf = weighted_confidence(
                regex_score=regex_score,
                proximity_score=img.caption_pattern_score,  # parser 가 채운 값
                vision_confidence=vr.confidence,
            )

            bidwatch_db.images.insert(
                doc_id=doc_id,
                sha256=vr.sha256,
                caption=vr.caption or regex_cap,
                image_type=vr.image_type,
                vision_confidence=vr.confidence,
                final_confidence=final_conf,
                auto_approved=final_conf >= 0.7,
                ai_cost_krw=vr.cost_krw,
                model=vr.model,
            )

        # 5-5. 위치 매핑 (같은 sha 가 여러 page 에)
        bidwatch_db.image_anchors.insert(
            doc_id=doc_id,
            sha256=img.sha256,
            page_no=img.page_no,
            bbox=img.bbox,
            bbox_unit=img.bbox_unit,
            order_in_page=img.order_in_page,
        )

    return doc_id
```

---

## 4. 비용 / 운영 가시성

```bash
# bidwatch 운영자가 Vision 누적 비용 확인
kdp-label --stats --cache-path /var/lib/bidwatch/kdp-cache.db
```

출력 (JSON):
```json
{
  "total_rows": 1234,
  "total_saved_krw": 856.40,
  "total_hit_count": 8201,
  "hit_rate": 0.869,
  "by_model": {
    "claude-haiku-4-5": {"rows": 1200, "saved_krw": 770.40, "hit_count": 8150},
    "claude-sonnet-4-5": {"rows": 34, "saved_krw": 86.00, "hit_count": 51}
  },
  "by_date": {
    "2026-05-24": {"rows": 22, "cost_krw": 14.15, "by_model": {...}}
  },
  "last_7_days_saved_krw": 856.40
}
```

→ bidwatch 의 비용 대시보드 / Grafana 에 그대로 입력 가능.

---

## 5. 주의 사항

### 5-1. BMP 호환성 (운영 진입 전 검증)

HWP 의 `bindata/` 가 PNG / JPEG **+ BMP** 를 emit. Vision API 가 BMP 거부할
가능성. **bidwatch 본격 운영 전 단일 BMP 로 1회 검증** (약 1원, `kdp-label
sample.bmp`). 거부 시 호출자 측에서 PIL 로 PNG 변환 후 호출.

자세한 내용: [`docs/internal/known-limitations.md`](../../internal/known-limitations.md)
의 § A-1.

### 5-2. AGPL 격리

`korean-doc-parser-hwp` 가 AGPLv3+ 라 bidwatch 의 라이선스 정책 확인:
- bidwatch 가 SaaS 라면 source 공개 의무 발생 (AGPL의 network use 조항)
- HWP 안 쓰면 코어 MIT 만으로 충분

### 5-3. tempfile 정리

`ExtractedImage.file_path` 는 라이브러리가 만든 tempfile. **bidwatch 가 본인
storage 로 복사** 후 사용 권고. tempfile 의 자동 정리는 라이브러리가 책임
지지 않음 (OS 의 tmp 회수 정책에 의존).

### 5-4. dedup 정책

PPTX 의 같은 이미지가 여러 슬라이드에 등장 (qvan storyboard 의 50 unique ×
평균 10 슬라이드 = 499 ExtractedImage). bidwatch 가 위 § 3 의 `seen_sha` 처럼
sha256 으로 dedup 권고. Vision cache 가 2회차 이후 0원이지만 row 증가는 막음.

### 5-5. bbox_unit 호환

`detect_caption_proximity` 호출 시 image + text bbox 가 같은 단위여야 함
(`bbox_unit == "px"` 끼리 또는 `"emu"` 끼리). 다른 단위 섞으면 거리 계산
무의미. HWP / HWPX / DOCX 는 `bbox_unit="none"` 이므로 proximity 미사용.

---

## 6. 한 줄 요약

> bidwatch 는 `extract()` + `VisionClient.label()` + `pipeline.*` 만 호출,
> 모든 저장은 자체 PostgreSQL. 라이브러리의 SQLite cache 는 비용 최적화용
> (운영 가시성은 `kdp-label --stats`). BMP 호환성과 AGPL 격리는 운영 진입
> 전 확인.
