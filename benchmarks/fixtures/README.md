# benchmarks/fixtures — 25건 픽스처 수집 가이드

> 이 디렉토리는 **저작권 안전한 픽스처만** 들어갑니다. 회사 자산(예: (주)렛츠 제안서 원본) 절대 금지.

## 1. 픽스처 3중 출처 (CLAUDE.md 규칙)

| 출처 | 목표 건수 | 비고 |
|---|---:|---|
| 자체 합성 | 15 | LaTeX→PDF, python-docx→DOCX, python-pptx→PPTX, 한글 데모 등으로 직접 생성 |
| 공공 도메인 | 10 | data.go.kr / 정부 공고 (공공누리 1유형) — 라이선스 표기 의무 확인 |
| 익명화 추출 | 옵션 | 회사명·금액·연락처 redact 후 구조만 보존. private repo 한정 |

**합계: 25건.** Phase 0 출구 게이트의 "벤치마크 결과 표" 요구치를 충족하는 최소량.

## 2. 포맷 분포 (7포맷 — HWP/HWPX/PDF/DOCX/DOC/PPTX/PPT)

| 포맷 | 최소 건수 | 비고 |
|---|---:|---|
| PDF | 6 | 텍스트형 4 + 스캔(OCR) 2 |
| DOCX | 4 | 표 포함 2 / 이미지 포함 2 |
| HWPX | 4 | 정부 공문 양식 위주 |
| HWP | 3 | pyhwp + 한/글 COM 폴백 검증 |
| PPTX | 3 | LibreOffice 변환 경유 |
| DOC | 3 | DOC→DOCX 변환 경로 |
| PPT | 2 | PPT→PPTX 변환 경로 |

도메인 분포는 5종(입찰공고/법률검토/공문/전람회/제안서)을 가능한 한 고르게.

## 3. Ground truth JSON 스키마

각 픽스처 옆에 동일 이름 + `.gt.json` 으로 둡니다.
예: `pdf_bid_001.pdf` ↔ `pdf_bid_001.pdf.gt.json` (또는 `pdf_bid_001.gt.json`)

```json
{
  "expected_keywords": ["입찰공고", "낙찰자", "예정가격"],
  "expected_table_count": 3,
  "expected_image_count": 2,
  "expected_text_length_range": [1500, 8000],
  "tolerance": {"table": 1, "image": 2},
  "_source": "data.go.kr/공공누리 1유형 / 자체합성 / 익명화",
  "_domain": "입찰공고",
  "_notes": "스캔본 — OCR 품질에 따라 점수 달라질 수 있음"
}
```

필드 의미:
- `expected_keywords`: 본문에 등장해야 할 핵심 키워드 — 부분 문자열 매칭
- `expected_table_count`: 정확값. `tolerance.table` 만큼 오차 허용
- `expected_image_count`: 정확값. `tolerance.image` 만큼 오차 허용
- `expected_text_length_range`: `[min, max]` — 추출 텍스트 길이 sanity check
- `_source` / `_domain` / `_notes`: 메타. 점수에 영향 없음

## 4. 작성 절차 (한 건 추가 시)

1. 원본 파일을 이 디렉토리 또는 하위(`pdf/`, `docx/` 등)에 저장
2. 사람이 직접 열어서 표/이미지 개수 세고, 핵심 키워드 5개 정도 뽑음
3. `.gt.json` 작성
4. `python benchmarks/compare.py --format <ext>` 로 단발 검증
5. 모든 어댑터 점수가 0 이면 GT 가 비현실적일 가능성 — 재검토

## 5. 절대 금지

- (주)렛츠 보유 제안서 원본 — 회사 자산
- 거래처 비공개 문서 — NDA 위반 위험
- 라이선스 불명확한 인터넷 수집 PDF

## 6. 현재 상태

- 수집 0건. **Phase 0 후반의 가장 큰 작업 항목** (worklog/000 §5-1 명시).
- 수집 완료 후 `worklog/001_phase0_benchmark_decision.md` 에 결과 정리.
