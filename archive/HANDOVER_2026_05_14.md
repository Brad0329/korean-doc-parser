# doc_parser — 프로젝트 인수인계 문서

> **현재 상태 (2026-05-24):** **v0.2.1 출시 완료** — PDF / DOCX / HWP / HWPX 4포맷.
> 본 문서는 **historical record** (2026-05-14 작성, lets_portal → doc_parser 분리 시점의
> 인수인계 컨텍스트). 그 시점의 결정 / Phase 0 출구 게이트 / Phase 1 합격 기준 등이
> 작성된 그대로 보존되어 있으며, **이후 마일스톤은 `worklog/` 의 누적 기록**에서 추적합니다.
>
> **새 세션 시작 시 우선순위:**
> 1. CLAUDE.md (코딩 규칙 + § "금지 의존성") 정독
> 2. 가장 최신 worklog (현재: `worklog/009_no_libreoffice_decision.md`, `worklog/008_v0.2.1_release.md`) 의 § 5 / § 7 "다음 세션이 알아야 할 것"
> 3. (선택) 본 문서의 § 1 (배경) + § 4 (1차 작업 교훈) + § 2 (확정 설계) 로 전체 맥락 보강
>
> 본 문서의 Phase 1~4 일정 / 합격 기준은 v0.1.0 시점 가설이며, 실제 출시 흐름은
> CHANGELOG.md 와 worklog/ 를 권위 있는 출처로 봅니다.
>
> **2026-05-24 영구 정책 변경:** 본 문서가 가정한 **"7포맷"** 은 **"5포맷"** 으로
> 축소되었습니다 (LibreOffice 도입 금지 결정). DOC / PPT 는 영구 미지원, PPTX 는
> markitdown 위임. 자세한 의사결정은 `worklog/009_no_libreoffice_decision.md`.

---

## 0. 이 문서 사용법

- **2026-05-14 작성된 historical document.** 프로젝트 배경 / 1차 작업 교훈 / Phase 0
  의사결정 / 패키지 명명 결정 등 분리 시점의 결정 사항을 보존합니다.
- 본 문서의 § 9 "첫 세션 체크리스트", § 3 "결정 필요 사항" 등은 **이미 모두 완료**
  되었습니다 (Phase 0 출구 게이트는 본문 § 6-1 의 ✅ 마킹 참고).
- v0.1.0 이후의 **마일스톤 / 의사결정 / 잠재 과제**는 모두 `worklog/*.md` 에 기록됩니다.

---

## 1. 프로젝트 배경

### 1-1. 어디서 왔는가
- **모체:** `lets_portal/backend/utils/file_parser.py` (526줄, Phase C-1 에서 작성, Phase D 에서 PPTX 추가)
- **모체의 검증 이력:** PDF 12건 / HWPX 1건 / DOCX 1건 / HWP 9건 / PPTX 1건 실전 파싱 통과
- **모체의 사용처:** lets_portal 의 AI 공고 분석(C-1~C-4), 마스터 프로필 추출(C-5), 회사 프로필 자동 채우기(C-5-B), 범용 파서(D)

### 1-2. 왜 분리하는가
1. **여러 프로젝트에서 재사용** — bidwatch 외에도 향후 RAG/문서분석 프로젝트가 늘어날 예정. lets_portal 안에 두면 cp 반복 + drift 발생
2. **품질 기준을 라이브러리 수준으로 끌어올림** — 테스트, CI, 패키징, 버전, 영문 docs. lets_portal 내부 도구로는 도달 불가
3. **단일 파일 포터빌리티 원칙을 제도화** — 외부 의존 0건, ParseResult 인터페이스 안정성을 계약으로 명문화
4. **HWP/HWPX 차별화 가치를 명확히** — markitdown/marker/docling 등 글로벌 마크다운 변환기 시장에서 비어 있는 한국 문서 영역을 정직하게 점유

### 1-3. 목표 (한 문장)
> **한국어 공공·민간 문서(HWP/HWPX/PDF/DOCX/DOC/PPTX/PPT)를 마크다운 + 이미지 + 메타데이터로 안정적으로 변환하는 라이브러리. 단일 파일 코어 + 옵션 확장 + 검수 파이프라인 3계층.**

> **포맷 결정 이력 (2026-05-15):** 지원 포맷 5종 → **7종 확장**. DOC/PPT 는 LibreOffice 로 DOCX/PPTX 자동 변환 후 기존 파서 재사용. PPTX 가 이미 LibreOffice 경유 방식이라 동일 컨버터 재활용.

---

## 2. 확정된 설계 결정 (이미 합의됨)

### 2-1. 2계층 아키텍처
- **하층 (Engine):** `file_parser.py` 업그레이드. 순수 추출, DB/AI/UI 의존 0건. 단일 파일 포터빌리티 유지.
- **상층 (Pipeline):** `DocumentIngestionPipeline` 클래스. 상태 관리(pending/auto_approved/needs_review/...), Claude Vision 라벨링, 검수 큐 운영. 옵션 패키지로 분리.

### 2-2. 라이선스 분리
- **코어 (PDF/DOCX/DOC/HWPX/PPTX/PPT):** MIT — pyhwp 의존 없음, 깨끗. DOC/PPT 는 LibreOffice 변환 경유
- **HWP extras:** GPL v3 격리 — `pip install korean-doc-parser[hwp]` 옵트인. pyhwp 가 GPL v3 라이브러리라 viral 영향이 있어서 분리
- **Pipeline:** MIT (Claude SDK 의존)

### 2-3. 단일 파일 포터빌리티 원칙
- 코어 엔진(`file_parser.py`) 은 **단일 파일 복사 가능** 상태 유지
- 외부 import 0건 (프로젝트 특정 모듈 절대 안 됨)
- 옵션 의존성은 import 시점 로드 (미설치 환경 graceful fallback)

### 2-4. 포지셔닝
- ❌ "Document Parser" / "Universal Parser" — markitdown 과 정면충돌, 못 이김
- ✅ **"Korean Document Parser"** — HWP/HWPX 차별화. 정직.
- repo 이름: `korean-doc-parser` 또는 `kdp` 또는 `hwp-markitdown` (Phase 0 에서 확정)
- 슬로건: **"HWP-aware alternative to markitdown for Korean documents"**

### 2-5. 이미지 추출 + Active Learning (지금 합의된 기능)
- 엔진은 이미지를 추출하고 메타데이터(페이지, bbox, 주변 텍스트, sha256, 1차 캡션) 까지 캡쳐
- 파이프라인은 Claude Vision 으로 캡션/타입/신뢰도 추론
- **3중 가중 신뢰도:** 정규식(0.4) + 레이아웃 근접도(0.2) + Vision 자가평가(0.4)
- **자동 분기:** confidence ≥ 0.9 AND caption 존재 → auto_approved, 그 외 → needs_review
- **검수 UI:** 단축키 기반(Y/N/J/K/E), 일괄 처리 지원
- **메타데이터 세트** — § 2-7 참조

### 2-6. 패키지 구조 (확정)
```
korean-doc-parser/                      ← GitHub repo
├── packages/
│   ├── core/                           ← pip install korean-doc-parser
│   │   ├── pyproject.toml              MIT
│   │   ├── src/korean_doc_parser/
│   │   │   ├── __init__.py             # public API
│   │   │   ├── core.py                 # ParseResult, ExtractedImage, BaseParser, registry
│   │   │   ├── parsers/
│   │   │   │   ├── pdf.py
│   │   │   │   ├── docx.py
│   │   │   │   ├── hwpx.py
│   │   │   │   ├── pptx.py             # LibreOffice 변환 경유
│   │   │   │   └── _libreoffice.py     # DOC→DOCX, PPT→PPTX 공용 컨버터
│   │   │   ├── tables.py
│   │   │   ├── captions.py             # regex/proximity 1차 캡션 검출
│   │   │   └── exceptions.py
│   │   └── tests/
│   ├── hwp/                            ← pip install korean-doc-parser[hwp]
│   │   ├── pyproject.toml              GPL v3 (pyhwp 의존)
│   │   ├── src/korean_doc_parser_hwp/
│   │   │   ├── __init__.py             # register_parser(HwpParser)
│   │   │   └── parser.py               # pyhwp + 한/글 COM 폴백
│   │   └── tests/
│   └── pipeline/                       ← pip install korean-doc-parser-pipeline
│       ├── pyproject.toml              MIT (Claude SDK 의존)
│       ├── src/korean_doc_parser_pipeline/
│       │   ├── __init__.py             # DocumentIngestionPipeline
│       │   ├── pipeline.py
│       │   ├── vision_labeler.py       # Claude Vision 래퍼
│       │   ├── confidence.py           # 3중 가중
│       │   └── manifest.py
│       └── tests/
├── examples/
│   ├── basic_text_extract.py           # 가장 단순 사용
│   ├── with_images.py                  # 이미지 추출 포함
│   ├── full_pipeline_with_review.py    # 검수 UI 까지
│   └── lets_portal_adapter.py          # lets_portal 호환 어댑터
├── docs/
│   ├── ko/                             # 한국어
│   ├── en/                             # 영문 (필수 — Korean Document 시장 외 한국 개발자도 영문 검색)
│   └── benchmarks/                     # § 4-1 참조
├── benchmarks/
│   ├── compare.py                      # markitdown/marker/docling vs ours
│   └── results/
├── .github/workflows/
│   ├── ci.yml                          # Ubuntu/macOS/Windows × Python 3.10~3.12
│   └── benchmark.yml                   # PR 마다 회귀 측정
├── CHANGELOG.md
├── LICENSE                             # 루트 LICENSE 는 MIT, packages/hwp/LICENSE 만 GPL
├── README.md                           # 영문 메인
├── README.ko.md
└── HANDOVER.md                         # 이 문서 (작업 시작용)
```

### 2-7. 메타데이터 세트 — `ExtractedImage`
사용자가 "하나의 메타데이터 세트로 묶어 저장" 하라고 명시하신 항목:

```python
@dataclass
class ExtractedImage:
    # === 위치 ===
    page_no: int | None              # PDF/PPTX
    section_no: int | None           # HWPX
    bbox: tuple[float, float, float, float] | None  # PDF only
    order_in_page: int               # 같은 페이지 내 순번

    # === 본문 컨텍스트 (엔진이 채움) ===
    text_before: str                 # 이전 200자
    text_after: str                  # 이후 200자
    section_title: str | None        # 속한 섹션 제목

    # === 파일 ===
    file_path: str                   # 영구 또는 tmp 경로
    sha256: str                      # 중복 detection
    width: int
    height: int
    size_bytes: int
    mime_type: str                   # image/png 등

    # === 1차 캡션 검출 (엔진의 결정적 로직) ===
    detected_caption: str | None     # regex 매칭 결과
    caption_method: str | None       # "regex" | "proximity" | None
    caption_pattern_score: float     # 0~1
```

파이프라인 단계에서 추가로 채워지는 필드 (DB 컬럼):

```
ai_caption, ai_image_type, ai_confidence, ai_reasoning, ai_model, ai_cost_krw
status (pending/auto_approved/needs_review/user_approved/rejected)
final_caption, reviewed_by, reviewed_at
```

---

## 3. 결정 필요 사항 (작업 시작 전 답할 것) ✅ **확정 완료 (2026-05-15)**

**5가지 모두 답이 나오기 전 코드 시작 금지.** 1차 작업의 실패 원인은 의사결정 단계를 건너뛴 것입니다.

> **결정 요약 (2026-05-15):**
> ① 회사 내 생산 자료 5종(입찰공고/법률검토/공문/전람회 PDF/제안서) ② 사내 private (bidwatch 향후 사용) ③ 유지보수 약속 없음 ④ 코어 MIT + HWP GPL v3 분리 ⑤ segmenter 일단 가져감 (4개 도메인 upgrade 필요) ⑥ repo 이름 `korean-doc-parser`
> + 추가 결정: DOC/PPT 도 포함 (LibreOffice 변환 경유, 7포맷)

### 3-1. 미래 프로젝트 시나리오 3~5개 ✅
> "앞으로 있을 많은 프로젝트에 적용해서 쓸 수 있도록" 이라고 말씀하셨음

**결정 (2026-05-15):** 회사 내에서 생산하는 자료 5종에 사용

| # | 도메인 | 포맷 (예) | segmenter 후속 작업 |
|---|--------|----------|---------------------|
| 1 | **입찰공고문** (일부) | PDF/HWP | `(공고 항목, 요구사항)` 쌍 — 신규 개발 |
| 2 | **법률검토 자료** | DOCX/HWP | `(질의, 회신)` 쌍 — 신규 개발 |
| 3 | **공문 자료** | HWP/PDF | 메타 위주 (수신/발신/일자) — 신규 개발 |
| 4 | **전람회 PDF** | PDF | 섹션 단위만 — 신규 개발 |
| 5 | **제안서** | DOCX/HWP/PDF | `(평가항목, 우리 역량 근거)` — **현재 보유** |

**1차 호출자:** bidwatch 서비스 (향후). 그 외 사내 RAG/검색 프로젝트.

### 3-2. 공개 OSS vs 사내 private repo ✅
**결정 (2026-05-15): 사내 private.** 향후 bidwatch 서비스 출시 시 함께 사용. 공개 검토는 무기한 보류 (③ 와 정합).

**함의:**
- 영문 docs 의무 **삭제** — 한글만 유지
- 이슈 응답 SLA **삭제**
- 라이선스 책임 외부 노출 0 — 단, 사내 의존 프로젝트(bidwatch) 가 있으니 SemVer 의무는 유지

### 3-3. 유지보수 약속 가능한가? ✅
**결정 (2026-05-15): 약속 없음.** → ② 의 "사내 private" 결정과 정합. 공개 OSS 가 아니므로 외부 SLA 없음.

**단, 사내 정합성은 유지:**
- bidwatch 운영 중 발견된 버그 → 회귀 테스트로 추가
- 의존성 보안 알림은 모니터링 (분기 1회 점검)
- Python 새 버전은 사내 운영 버전이 따라갈 때 같이 호환

### 3-4. 라이선스 분리 OK? ✅
**결정 (2026-05-15): 추천대로 (코어 MIT + HWP extras GPL v3 격리).**

- `packages/core/` (PDF/DOCX/DOC/HWPX/PPTX/PPT) → MIT
- `packages/hwp/` (pyhwp 의존) → GPL v3 — `pip install korean-doc-parser[hwp]` 옵트인
- `packages/pipeline/` → MIT (Claude SDK)

사내 private 이라 외부 라이선스 충돌 위험은 낮지만, 향후 공개 검토 가능성 대비 분리 유지.

### 3-5. lets_portal 의 다른 모듈도 같이 가져갈지? ✅
**결정 (2026-05-15): segmenter 만 가져감.** 단, 현재 segmenter 는 **제안서 도메인 전용** (Phase D-2 매칭률 90.4% 는 제안서 한정 수치).

**함의 (중요):**
- v0.1 출시 시 segmenter 는 **제안서 1종만** — 다른 4종 도메인(입찰공고/법률검토/공문/전람회) 은 미동작 상태로 두고 후속 마일스톤
- segmenter 패키지를 도메인-pluggable 구조로 설계 의무 (BaseSegmenter + ProposalSegmenter, BidNoticeSegmenter 등)
- v0.2~v0.5 에서 도메인별 segmenter 1개씩 추가

**가져오지 않는 모듈:**
- `backend/extractors/proposal.py` (Claim 추출) — lets_portal 도메인 특화, doc_parser 영역 아님
- `backend/utils/text.py` (clean_html 등) — 작아서 굳이 이전 불필요, 필요시 자체 구현

---

## 4. 1차 작업에서 배운 것 (반복 금지)

### 4-1. 경쟁 라이브러리 검토를 빠뜨림 (가장 큰 실수)
- markitdown, marker, docling, unstructured — **설계 문서에 한 번도 등장 안 함**
- 이미 알고 있던 pdfplumber/python-docx 로 직진 → PDF/DOCX/PPTX 가 "commodity 수준" 으로 끝남
- **이번엔 Phase 0 에서 의무적으로 벤치마크.** 동일 샘플 25건에 5개 경쟁 라이브러리 + 현 file_parser 돌려서 수치로 비교. 결과 표가 나와야 "어디는 위임, 어디는 자체 구현" 결정이 객관적으로 됩니다.

### 4-2. 테스트 0건
- 1차 작업 코드 600줄에 unit test 하나 없음
- 검증은 "실제 샘플 돌려보고 잘 나오면 됨" — 회귀 보장 0
- **이번엔 TDD.** 픽스처 + ground truth 가 코드보다 먼저.

### 4-3. 단일 샘플 의존 (조용한 실패)
- D-1 진단에서 발견: 파서가 경과원 ESG 1종 형식에만 동작. 신규 제안서는 섹션 0개로 "정상 완료" 처리됨
- 원인: MVP 검증을 단일 샘플로 마감
- **이번엔 합격 기준에 "샘플 10건 모두 통과" 명시.** 단일 케이스 OK 로 다음 단계 진행 금지.

### 4-4. 정책 결정이 흔들림 (PPTX)
- 2026-04-22: PPTX 미지원 결정
- 2026-05-14: 똑같은 근거가 약해서 자동 변환으로 뒤집힘
- 원인: 결정 근거 표면("샘플 1/10 ROI") 과 진짜 근거(다운스트림 미스매치) 가 섞임
- **이번엔 결정 시 "표면 근거" vs "진짜 근거" 분리 명시.** 표면 근거만 적으면 나중에 흔들림.

### 4-5. 단일 파일 강제로 모듈 분리를 못 함
- 1차 작업의 단일 파일 526줄은 함수 17개, 책임 5개(PDF/HWPX/DOCX/HWP/공용표) 가 한 파일에
- **이번엔 단일 파일 제약을 코어에만 적용.** 코어 안에서도 `parsers/pdf.py`, `parsers/docx.py` 분리. 외부 사용자에겐 단일 패키지로 보이지만 내부는 깨끗.

---

## 5. 가져갈 산출물 (lets_portal → doc_parser)

### 5-1. 필수 (시작 시 즉시 복사)

| lets_portal 의 파일 | 새 위치 | 처리 |
|---|---|---|
| `backend/utils/file_parser.py` | `packages/core/_legacy/file_parser.py` | **참조용**으로만. 새 코드는 처음부터 다시. 단, HWP/HWPX 추출 로직은 검증된 가치 있어 패키지로 분리해서 이전 |
| `backend/utils/file_parser.md` | `docs/ko/legacy_notes.md` | 1차 작업 이식 가이드 — 새 README 작성 시 참조 |
| `work_log2/log_phaseD.md` | `docs/ko/phase_d_lessons.md` | D-1/D-2 교훈 + PPTX 정책 변경 기록. **그대로 가져가서 새 프로젝트의 baseline knowledge** |
| `work_log2/design_phase_d_parser.md` | `docs/ko/segmenter_design.md` | segmenter 가져갈 경우 함께 |
| `backend/extractors/segmenter/` | `packages/segmenter/src/` | § 3-5 결정 시 함께 (전체 디렉토리, 4파일) |
| 이 문서 (`doc_parser_handover.md`) | `HANDOVER.md` (repo 루트) | 새 프로젝트의 시작점 |

### 5-2. 샘플 데이터 (저작권 처리 후)

| lets_portal 의 데이터 | 처리 |
|---|---|
| `data/proposal_sample/` 10건 ((주)렛츠 제안서) | **공개 repo 면 절대 금지.** Private 도 회사 자산이라 신중. 처리 옵션: (a) 회사명/금액/연락처 redact 후 사용, (b) 자체 합성 데이터로 대체, (c) 공공 도메인 문서로 교체 (공공누리 1유형) |
| `data/diag_d1/`, `data/diag_d2/` | 1차 작업 진단 결과. 새 벤치마크에서 baseline 으로 활용 가능 |

### 5-3. 1차 작업 산출 코드 (참조용)

| lets_portal 의 코드 | 가치 |
|---|---|
| `_parse_hwp` + `_xhtml_to_markdown` (file_parser.py 309~498) | **HWP 처리의 핵심 자산.** pyhwp + 한/글 COM 이중 폴백 + XHTML 마크다운 변환. 새 코드의 `packages/hwp/` 의 기반 |
| `_parse_hwpx` + `_hwpx_extract_node` (file_parser.py 146~250) | HWPX 직접 XML 파싱. 글로벌 라이브러리 거의 안 함. 그대로 이전 후 테스트 추가 |
| `_parse_pptx` (file_parser.py LibreOffice 변환) | 2026-05-14 추가. 검증 미완(운영 서버 검증 필요) 상태로 이전. doc_parser 에서 정식 테스트 추가 |

---

## 6. 추천 작업 순서

### Phase 0 — 의사결정 (3일, 코드 0줄)
- **Day 1:** § 3 의 5가지 결정 사항 답 적기. 미래 프로젝트 시나리오 3~5개를 한 줄씩 적기 (이게 가장 어려움 — 시간 들여서)
- **Day 2-3:** 경쟁 라이브러리 벤치마크 스크립트 작성 + 실행
  - 동일 샘플 25건에 markitdown / marker / docling / unstructured / 현 file_parser 돌리기
  - 측정: 텍스트 완성도, 표 보존율, 처리 시간, 메모리, 의존성 무게
  - 결과 표로 정리

**Phase 0 의 출구 게이트: ✅ 통과 완료 (2026-05-20)**
- [x] § 3 답 모두 작성됨 (2026-05-15)
- [x] 벤치마크 결과 표 생성됨 — `benchmarks/results/phase0_20260518T060334Z.{json,md}`
- [x] "어디는 위임 / 어디는 자체" 결정 명문화됨 — `worklog/001_phase0_benchmark_decision.md`

→ **Phase 1 진입 가능**

### Phase 1 — v0.1 빌드 (2주)
- **Week 1:**
  - Day 1-2: repo 부트스트랩 (pyproject.toml × 3 패키지, `__version__`, ruff/mypy/pytest 설정, CI)
  - Day 3: 테스트 픽스처 작성 (합성 30 + 공공도메인 20)
  - Day 4-5: 코어 엔진 PDF/DOCX (markitdown 위임 어댑터 또는 자체 — Phase 0 벤치마크 결과에 따라)
- **Week 2:**
  - Day 6-7: HWPX 자체 구현 + 테스트
  - Day 8-9: HWP extras 패키지 (1차 코드 이전 + 정리 + 테스트)
  - Day 10: PPTX + PPT + DOC (LibreOffice 공용 컨버터 한 번 만들고 3 포맷 모두 검증)

**v0.1 합격 기준:**
- [ ] 7포맷(HWP/HWPX/PDF/DOCX/DOC/PPTX/PPT) 모두 텍스트 + 표 + 이미지 + 메타데이터 추출
- [ ] LibreOffice 변환 경로(DOC→DOCX, PPT→PPTX) 픽스처 각 최소 5건 통과
- [ ] pytest 커버리지 85%+
- [ ] CI 통과 (Ubuntu/macOS/Windows × Python 3.10~3.12)
- [ ] 영문 + 한글 README 동시 갱신
- [ ] CHANGELOG.md 첫 항목 작성

### Phase 2 — lets_portal 마이그레이션 (3일)
- **Day 1:** lets_portal 에 feature flag (`USE_NEW_PARSER=1`) 도입. 신/구 둘 다 import 가능
- **Day 2-3:** Shadow run. 둘 다 돌려 결과 diff 를 로그에 저장. 사용은 구 버전.
- **+1주 안정화:** diff 검토 → 차이 0 또는 신버전 우위 확인 → flag flip → 1주 후 구 file_parser.py 제거

### Phase 3 — Pipeline 패키지 (1주)
- DocumentIngestionPipeline 구현
- Claude Vision 라벨링 + 3중 신뢰도
- 검수 큐 API (FastAPI)
- 검수 UI (HTML/JS)
- lets_portal 의 새 RAG 흐름에 통합

### Phase 4 — Active Learning + 이미지 정제 (1주)
- 이미지 추출 정확도 측정
- 캡션 검출 정규식 튜닝
- OOXML 차트 데이터 추출 (옵션)
- 검수 UI 단축키/일괄처리 UX 폴리싱

**총 소요: 약 4.5주.** 풀타임 1인 기준.

---

## 7. 명명 / 포지셔닝 ✅ **확정 (2026-05-15)**

**결정: repo 이름 = `korean-doc-parser`. PyPI 패키지명/import 경로/슬로건 모두 § 7-1 ~ 7-4 의 추천안 그대로 채택.**


### 7-1. repo 이름 후보
| 후보 | 평가 |
|---|---|
| `korean-doc-parser` | 명확, 검색 친화적. **추천** |
| `kdp` | 짧지만 의미 불명 |
| `hwp-markitdown` | markitdown 차용 — 호의/적대 양면 |
| `doc-parser-kr` | 평이함 |

### 7-2. PyPI 패키지 이름
- `korean-doc-parser` (코어)
- `korean-doc-parser[hwp]` (HWP extras)
- `korean-doc-parser-pipeline` (별도 패키지)

### 7-3. import 경로
```python
from korean_doc_parser import extract, ParseResult
from korean_doc_parser_pipeline import DocumentIngestionPipeline
```

### 7-4. 슬로건
> "**HWP-aware document-to-markdown library for Korean documents.**
> A markitdown alternative with native HWP/HWPX support."

영문 슬로건이 정직하게 포지셔닝합니다.

---

## 8. lets_portal 과의 관계

### 8-1. 일시 공존 → 점진 교체
- lets_portal 은 doc_parser v0.1 안정화까지 **현 file_parser.py 그대로 사용**
- doc_parser v0.1 출시 시 lets_portal 에 feature flag 도입 (Phase 2)
- 안정 확인 후 lets_portal 의존성으로 `korean-doc-parser` 등록, 구 코드 제거

### 8-2. API 호환성 유지
- 현 `extract_text(file_path) → ParseResult` 인터페이스는 **그대로 유지 의무**
- 새 기능(이미지 등) 은 추가 파라미터로만 (기본값 False)
- Breaking change 시 SemVer major bump + 1년 deprecation 기간

### 8-3. 양방향 학습
- lets_portal 운영 중 발견된 파싱 실패 → doc_parser 의 회귀 테스트로 영구 추가
- doc_parser 의 개선 → lets_portal 에 backport (의존성 업그레이드로 자동)

---

## 9. 첫 세션 체크리스트 (구체)

새 doc_parser 디렉토리에서 첫 세션:

- [ ] 새 디렉토리 만듦: `~/Documents/doc_parser/` (또는 원하는 위치)
- [ ] 이 문서(`doc_parser_handover.md`) 를 `HANDOVER.md` 로 이동
- [ ] `doc_parser_CLAUDE.md` 를 `CLAUDE.md` 로 이동 (별도 파일, 같이 전달됨)
- [ ] `git init` + 초기 커밋 (`HANDOVER.md` + `CLAUDE.md` 만)
- [ ] 이 문서 § 0 ~ § 10 정독
- [ ] § 3 의 5가지 결정 사항 답 적기 (`HANDOVER.md` 본문에 직접 또는 별도 `decisions.md`)
- [ ] Phase 0 의 벤치마크 스크립트 작성
- [ ] 벤치마크 실행 후 결과 표 정리
- [ ] Phase 0 출구 게이트 통과 확인
- [ ] Phase 1 진입 (또는 결정에 따라 중단)

**의지가 흔들리는 순간 (Phase 0 마치고 "그냥 lets_portal 안에서 할까?" 라는 생각이 들면) 이 문서 § 1-2 "왜 분리하는가" 다시 읽기.**

---

## 10. 부록 — CLAUDE.md 이관 판단

### 10-1. 현 CLAUDE.md 분석

```
# lets_portal 작업 규칙

## 새 세션 시작 시
- work_log2/plan_2.md 확인 → 전체 현황/아키텍처/완료 Phase 파악
- 해당 Phase 작업 로그 확인 → 이전 결정사항/실패 경험 이어받기

## Agent 역할 분담
- 메인 agent: 코드 개발에 집중
- 테스트 agent (foreground): Phase 완료 시 통합 테스트

## 작업 로그 원칙
- 위치: work_log2/
- Phase 완료 시 메인 agent가 직접 작성
- 코드에서 알 수 없는 것만 쓴다:
  1. 결정의 이유 (코드는 What, 로그는 Why)
  2. 외부 제약 조건
  3. 실패한 접근과 원인
- 적지 않는 것: 코드 구현 상세, git 히스토리, 테스트 케이스 목록

## 테스트 규칙
- Phase 완료 → 별도 테스트 agent(foreground)가 통합 테스트
```

### 10-2. 이관 판단

| 항목 | 그대로 OK | 수정 필요 | 추가 필요 |
|------|---------|---------|---------|
| 새 세션 시작 시 plan 확인 | ❌ | ✅ 경로 변경 (`plan_2.md` → `HANDOVER.md` + 작업 로그) | |
| Agent 역할 분담 | ✅ | | |
| 작업 로그 위치 (`work_log2/`) | ❌ | ✅ → `docs/worklog/` 또는 `worklog/` | |
| 작업 로그 원칙 (이유/제약/실패) | ✅ | | |
| "적지 않는 것" 목록 | ✅ | | |
| 테스트 규칙 | △ | ✅ Phase 단위에서 PR 단위로 변경 (라이브러리는 Phase 개념 약함) | |
| **라이브러리 특화 규칙** | | | ✅ § 10-3 참조 |

### 10-3. 라이브러리 프로젝트에 추가해야 할 규칙

기존 CLAUDE.md 에 없던 항목 — 라이브러리는 애플리케이션과 책임이 다름:

1. **공개 API 변경 시 SemVer + CHANGELOG 갱신 의무**
2. **단일 파일 포터빌리티 원칙** — 코어 패키지(`packages/core/`) 는 외부 import 0건 유지. 위반 시 코드 머지 금지
3. **회귀 테스트 통과 의무** — 픽스처 25건 전수 통과 없이 main 브랜치 머지 금지
4. **영문 docs 동시 갱신** — 한국어 docs 만 갱신하고 영문 안 갱신하면 PR 거절
5. **코어/extras/pipeline 패키지 경계 침범 금지** — pipeline 이 hwp 를 직접 import 하지 않음 (의존성 inversion)
6. **벤치마크 회귀 ±5% 이내** — 처리 시간/메모리 회귀 시 PR 거절 또는 이유 명시
7. **이슈 응답 — 주 1회 이상** (공개 시)

### 10-4. 결론
> **현 CLAUDE.md 는 그대로 이관하지 말고, 별도 파일(`doc_parser_CLAUDE.md`) 으로 새로 작성한 버전을 함께 전달합니다.** 핵심 원칙(작업 로그/Agent 분담/테스트) 은 그대로 유지하되, 라이브러리 특화 항목 7가지를 추가하고 lets_portal 경로 의존성을 제거한 버전입니다.

이 별도 파일은 같은 디렉토리에 `doc_parser_CLAUDE.md` 로 함께 작성되어 있으니, 새 프로젝트에서 `CLAUDE.md` 로 이동시키시면 됩니다.

---

## 11. 한 줄 요약 — 다음 세션이 알아야 할 것

> doc_parser 는 lets_portal/backend/utils/file_parser.py 를 분리해 라이브러리 수준으로 끌어올리는 프로젝트. 2계층 아키텍처(엔진+파이프라인), 코어 MIT + HWP extras GPL 분리, 한국 문서(HWP/HWPX) 차별화 가치. 시작 전 § 3 의 5가지 결정 필요. Phase 0(3일 의사결정) → Phase 1(2주 v0.1) → Phase 2(3일 lets_portal 마이그) → Phase 3(1주 파이프라인) → Phase 4(1주 active learning). 1차 작업의 5가지 실수 반복 금지(§ 4).

---

**다음 세션, 처음부터 시작하세요. 이 문서가 컨텍스트 100% 입니다.**
