# Changelog

이 프로젝트의 모든 주목할 만한 변경사항을 이 파일에 기록합니다.

형식은 [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/) 을 따르고,
버전은 [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html) 을 준수합니다.

**SemVer 의무 (CLAUDE.md §"라이브러리 특화 규칙 §1"):**
public API (`korean_doc_parser/__init__.py` 노출 함수·클래스·타입) 변경 시
patch / minor / major 판단을 PR 본문 또는 commit 메시지에 명시합니다.

---

## [Unreleased]

(다음 마일스톤은 **v1.0.0 — 사내 stable lock**. worklog/020 § 5-5 의 남은
Phase: archive 정리 + 호출자 문서. v0.5.0 의 자산이 v1.0 으로 그대로 lock.)

---

## [0.5.0] — 2026-05-25

**Minor — Pipeline 알고리즘 모듈 + default Haiku 전환 + 코드 부채 3건 정리.**
worklog/019 의 b 안 (Pipeline = stateless 알고리즘만, DB / 큐 / UI 제거)
이행. SemVer minor — public API 확장 + default 동작 변경 (호환 가능).

자세한 내용은 `worklog/020_v0.5.0_release.md` 참고.

### Added

- **`korean_doc_parser.pipeline` sub-package** — 호출자 (bidwatch /
  vanasso.kr / 사내 RAG) 가 자체 ingestion flow 를 조립할 때 쓰는 pure
  function 모음:
  - `compute_doc_id(path)` → sha256(file_bytes) 64-char hex
  - `weighted_confidence(regex, proximity, vision, weights)` — 3중 가중
    (default 0.4/0.2/0.4 = worklog/011 § B), 0-1 clamp, customizable
  - `detect_caption_regex(text)` → 한국어 (`<그림 N>` / `[그림 N]` / `자료:`)
    + 영문 (`Figure N` / `Table N`) 패턴, 강도별 0.6-1.0 score
  - `detect_caption_proximity(image_bbox, text_blocks)` → 최근접 텍스트 +
    거리 기반 score (bbox-unit-agnostic, 같은 단위 가정)
  - `TextBlock` / `CaptionDetection` dataclass
- **`ExtractedImage.bbox_unit`** 필드 — `Literal["px", "emu", "none"]`. 각
  파서가 단위 메타 명시 (PDF=px, PPTX=emu, HWP/HWPX/DOCX=none).
  worklog/016 § 4-3 잠재 과제 해소
- **`VisionCache.hit_count`** 컬럼 + `stats()` 의 `total_hit_count` /
  `hit_rate` / per-model `hit_count` — worklog/015 § 4-1 schema 한계 해소.
  기존 v0.4.x cache.db 자동 마이그레이션 (idempotent ALTER TABLE)
- **`parsers/_imageutil.py`** — PPTX + HWP 의 `_safe_image_size` 중복 통합.
  worklog/017 § 4-4 코드 부채 해소

### Changed

- **default 모델 Sonnet → Haiku** — `vision/client.py` 의 `DEFAULT_MODEL`.
  CLI / Python API 의 default 동작 변경. worklog/014 의 22건 실측 정당화
  (비용 1/10.6, 품질 동등 93% 한국어, 더 정직한 confidence calibration).
  명시 호출 (`--model claude-sonnet-4-5`) 은 그대로 동작

### Migration

- **`ExtractedImage` 직접 생성하는 코드** 는 `bbox_unit` 키워드 인자 박아야 함.
  라이브러리 반환값만 받는 일반 호출자는 영향 없음
- **default 모델이 Haiku** — Sonnet 가정한 호출자는 모두 명시 호출이라 영향 0.
  default 그대로 쓰면 자동으로 비용 1/10 절감
- **cache hit_count** — 기존 v0.4.x cache.db 의 row 는 `hit_count = 0` 으로
  자동 마이그레이션. 이후 호출부터 누적

### Quality gates (실측)

- pytest: **232 통과** (v0.4.5 의 195 + pipeline 33 + cache hit_count 4)
- 전체 라인 커버리지: **91%+** (v0.4.5 동일)
- ruff + mypy strict + pre-commit: 모두 통과

---

## [0.4.5] — 2026-05-25

**Patch — HWP 이미지 추출 (worklog/007 § 2-3 deferred 해소).** SemVer patch:
공개 `__init__.py` API 동일. `ParseResult.images` 의 HWP 동작 변경
(v0.2 의 `[]` → v0.4.5 의 N건) 은 호환 가능한 채움.

자세한 내용은 `worklog/017_v0.4.5_hwp_image_extraction.md` 참고.

### Added

- **HWP 비트맵 추출** (`packages/hwp/src/.../parser.py`) — pyhwp 의 `bindata/`
  디렉토리 walk + 영구 tempfile 복사. worklog/007 § 2-3 의 "bbox 매핑 비자명"
  미진입 사유가 v0.4.4 의 PPTX (EMU 단위 그대로, 통일은 v0.5 Pipeline) 와
  같은 카테고리 결정으로 해소.
  - samples/ 5종 실측: test_nara **12**, proposal_gyeongnam_fishery **18**,
    렛츠 제안서 **22**, proposal_wku **55**, proposal_forest_startup **91**
    (v0.2 모두 0)
  - `page_no` / `bbox` = `None` — HWP 좌표계와 PDF-style bbox 매핑 없음 (정직)
  - `order_in_page` = pyhwp BinData stream 번호 (1-based, 결정론적)
  - PNG / JPEG / BMP MIME 인식. PIL fail 시 `(0, 0)` graceful
- **단위 테스트 4건** (test_hwp_parser.py) — images 비어있지 않음 + per-image
  contract + MIME 인식 + 빈 bindata graceful → 총 195 pytest 통과
- **`kdp-label --from-document some.hwp`** 가 처음으로 동작 — **5포맷 전수
  Vision 라벨링 자산화 완료**

### Milestone

- **5포맷 (PDF / DOCX / HWP / HWPX / PPTX) 모두 이미지 추출 가능.** 자산화
  우선 경로 (worklog/014 § 5-5) 완료. 남은 마일스톤은 v0.5.0 본체

### Known limitations (v0.5+ 후보)

- HWP 이미지의 `page_no` / `bbox` 복원 — pyhwp 의 record-level 접근으로
  이론적 가능, bidwatch 사용처에서 필요해지면 진입. worklog/017 § 4-1
- BMP 의 Claude Vision API 호환성 — Anthropic 이 BMP 거부할 가능성. v0.4.6 또는
  v0.5 의 graceful skip 후보. worklog/017 § 4-3
- `_safe_image_size()` 가 PPTX / HWP parser 양쪽에 중복 — v0.5+ 의
  `parsers/_imageutil.py` 로 통합 후보. worklog/017 § 4-4

### Quality gates (실측)

- pytest: **195 통과** (v0.4.4 의 191 + 4 신규 HWP 추출 테스트)
- 전체 라인 커버리지: **91%+** (v0.4.4 동일)
- ruff + mypy strict + pre-commit: 모두 통과

### Migration notes

- `ParseResult.images` 가 HWP 에서 처음 비어있지 않을 수 있음. 다운스트림에서
  `len(images) == 0` 을 HWP 의 invariant 로 가정한 코드는 갱신 필요
- `samples/*.hwp.gt.json` 의 `expected_image_count` 가 v0.2 시점 0 → v0.4.5
  시점 측정값으로 갱신 (사용자 로컬, samples/ 는 .gitignore)

---

## [0.4.4] — 2026-05-25

**Patch — PPTX 이미지 추출 (markitdown 위임 한계 해소).** SemVer patch:
공개 `__init__.py` API 동일. `ParseResult.images` 의 PPTX 동작 변경
(v0.3 의 `[]` → v0.4.4 의 N건) 은 호환 가능한 채움 (worklog/016 § 2-6).

자세한 내용은 `worklog/016_v0.4.4_pptx_image_extraction.md` 참고.

### Added

- **PPTX 비트맵 추출** (`parsers/pptx.py`) — markitdown 의 ``![](filename)``
  text placeholder 한계 (v0.3 / worklog/014 § 5-1) 를 python-pptx 직접 접근으로
  보완. shape walk + group 재귀 + 비표준 포맷 (.wdp) graceful degrade.
  - samples/ 3종 실측: 한국관광공사 제안서 **38**, lets_portal tmp **46**,
    QVAN storyboard **499** 이미지 추출 (v0.3 모두 0)
  - notes / master / layout 슬라이드는 제외 (사용자 명시 picture shape 만)
  - `bbox` 는 PPTX 의 native EMU (English Metric Unit) — PDF 의 px 단위와 다름.
    통일 정규화는 v0.5+ Pipeline 결정 항목 (worklog/016 § 4-3)
- **단위 테스트 5건** (test_pptx_parser.py) — 합성 픽스처 1건 추출 + 텍스트
  전용 PPTX 의 빈 리스트 + sha256 형식 + tempfile 영속성 + bbox EMU 계산
- **`build_pptx_with_image`** ground truth 갱신 — `expected_image_count` 0 → 1
- **`kdp-label --from-document some.pptx`** 가 처음으로 동작 — PPTX 사용자의
  Vision 라벨링 파이프라인 자산화 완료

### Known limitations (v0.5+ 후보)

- **같은 이미지의 슬라이드별 중복** — engine 은 raw 반환, Pipeline (v0.5) 의
  sha256 캐시가 자동 dedup. CLI 만 쓰면 같은 이미지 N회 추출 (caching 으로
  2회차 이후 0원이지만 row 증가). worklog/016 § 4-1
- **chart / smartart 미지원** — PICTURE shape 만. LibreOffice 변환은 CLAUDE.md
  §"금지 의존성" 위반이라 영구 차단. 매우 필요해지면 v0.5+ 에서 자체 렌더링
  옵션 재검토. worklog/016 § 4-2

### Quality gates (실측)

- pytest: **191 통과** (v0.4.3 의 186 + 5 신규 PPTX 추출 테스트)
- 전체 라인 커버리지: **91%+** (v0.4.3 동일 — 이미지 추출 경로 신규 100%)
- ruff + mypy strict + pre-commit: 모두 통과

### Migration notes

- `ParseResult.images` 가 PPTX 에서 처음 비어있지 않을 수 있음 (v0.3 부터
  `[]` 만 반환했던 동작이 v0.4.4 에서 N건 반환으로 변경). 다운스트림에서
  `len(images) == 0` 을 PPTX 의 invariant 로 가정한 코드는 갱신 필요
- `samples/*.pptx.gt.json` 의 `expected_image_count` 가 v0.3 시점 0 → v0.4.4
  시점 측정값으로 갱신됨 (사용자 로컬). 새 PC 에서 samples 받으면 같은
  갱신 필요 — 자동화 스크립트는 v0.5+

---

## [0.4.3] — 2026-05-25

**Patch — `kdp-label --stats` 운영 가시성.** SemVer patch:
공개 `__init__.py` API 동일, CLI 명령 1개 + 내부 stats() 확장만.

자세한 내용은 `worklog/015_v0.4.3_kdp_label_stats.md` 참고.

### Added

- **`kdp-label --stats`** — cache SQLite 의 누적 상태를 JSON 으로 출력 +
  exit. Anthropic API 호출 없음.
  - `total_rows` / `total_saved_krw` / `by_model {rows, saved_krw}` /
    `by_date {YYYY-MM-DD: {rows, cost_krw, by_model}}` / `last_7_days_saved_krw`
  - cache 파일 없으면 silent create 거부 + 친절한 에러 (typo 보호)
  - `--output` 으로 파일에 저장 가능
- **`VisionCache.stats()` 확장** — 기존 `total_rows + by_model` 에 `by_date` +
  `total_saved_krw` + `last_7_days_saved_krw` 추가. 내부 API.

### Known limitations (v0.5.0 에서 해소 예정)

- cache **hit rate** 미측정 — schema 에 hit_count 컬럼 없음. v0.5.0 의
  PostgreSQL 마이그레이션에서 schema 재설계 시 같이 (worklog/015 § 4-1)
- JSON 출력만 — 사람 친화 표는 `jq` 로 처리하거나 v0.5+ 의 `--format table`

### Quality gates (실측)

- pytest: **186 통과** (v0.4.2 의 178 + 8 신규: cache 4 + cli 4)
- 전체 라인 커버리지: **91%+** (v0.4.2 동일)
- ruff + mypy strict + pre-commit: 모두 통과

---

## [0.4.2] — 2026-05-25

**Patch — Sonnet vs Haiku 실 이미지 22건 비교 평가.** SemVer patch:
공개 API 동일, 평가 결과 + 자동화 스크립트 추가만.

자세한 내용은 `worklog/014_v0.4.2_haiku_evaluation.md` 참고.

### Added

- **`scripts/eval_haiku.py`** — 모델 비교 측정 자동화. 인자로 받은 문서에서
  이미지 추출 → sha256 결정론적 정렬 → N개 모델로 순차 라벨링 →
  `{out_dir}/{model}.jsonl` + `summary.json` (per-model + cross-model
  agreement + cost ratio). cache 비활성 default (cold 측정), `--cache` 옵션.
  향후 모델 추가 시 재사용 가능 (e.g. Opus 진입 시).
- **`.gitignore`** — `eval_v*/` 패턴 추가 (raw 측정 산출물 untracked, 수치는
  worklog 에만 박음).

### Verified (실 Anthropic API — 22 이미지 cold call)

평가 자료: `samples/키움증권_스테이블코인.pdf` (50 이미지 중 ≥100x100 22건).

| 지표 | Sonnet | Haiku | 비교 |
|---|---:|---:|---|
| cost / image | 6.85원 ($0.00496) | **0.64원 ($0.00047)** | Haiku 1/10.6 |
| wall time / image | 4.80초 | **2.77초** | Haiku 1.7배 빠름 |
| hangul_ratio (mean) | 93.0% | **93.3%** | 동등 |
| confidence ≥ 0.7 비율 | 100% (calibration 평탄) | **86.4%** (정직) | Haiku 가 검수 큐 정렬 가능 |
| image_type agreement | — | — | **84.2%** (16/19, 모호 케이스 3건) |
| 2-pass trigger | 0/22 | **3/22** | worklog/011 B.1 의 2-pass 전략 처음으로 동작 |

**5/5 합격 기준 양 모델 모두 통과.** worklog/011 § A.1 의 "한국 차트 caption
품질 우려" 가설은 **22건 실 이미지에서 근거 없음**으로 판명 → v0.5.0 default
전환 정당화.

### Decided (v0.5.0 에서 실행)

- **default 모델 Sonnet → Haiku 전환** — 시나리오 A (v0.4.2 = 평가만, 전환은
  v0.5.0 의 minor bump). 진짜 근거: 검수 큐 정렬이 Haiku 의 calibrate 된
  confidence 에서만 의미를 가짐 (worklog/014 § 4-2). 사용자가 정밀이 필요하면
  `--model claude-sonnet-4-5` 명시.

### Known limitations (v0.4.x 잠재 과제)

- PPTX `extract().images` 가 0건 (markitdown 위임 한계) — v0.5 또는 v0.4.3
  patch 후보. worklog/014 § 5-1 참고
- PDF 중복 이미지 (같은 sha256 이 여러 페이지에 등장) dedup 정책 미정 →
  Pipeline (v0.5) 의 sha256 캐시로 자연 해소. worklog/014 § 5-2 참고

### Quality gates (실측)

- pytest: **178 통과** (v0.4.1 동일, 코드 변경 0건)
- 전체 라인 커버리지: **91%+** (v0.4.1 동일)
- ruff + mypy strict: 통과 (`scripts/` 는 ruff 만 적용, mypy 검사 대상 밖)

---

## [0.4.1] — 2026-05-25

**Patch — 실 Vision API 평가 통과 + `.env` 자동 로드.** SemVer patch:
공개 API 동일, CLI 의 편의 기능 추가 + 평가 결과 박힘.

자세한 내용은 `worklog/013_v0.4_vision_evaluation.md` 참고.

### Added

- **`.env` 자동 로드** (`cli/label.py`, `_load_dotenv()`):
  - 루트 `.env` 파일에 `ANTHROPIC_API_KEY=...` 박아두면 `kdp-label` 실행 시
    자동 로드 (python-dotenv 의존성 0, ~15줄 자체 파싱)
  - KEY=VALUE / KEY="VALUE" / KEY='VALUE' 모두 지원
  - 주석 (`#`) / 빈 줄 건너뛰기
  - 기존 환경변수가 **비어있을 때만** 덮어씀 (Windows PowerShell 의 빈
    env var propagation quirk 처리)
- **단위 테스트 4건 추가** — dotenv 파싱 / missing file / non-empty 보호 /
  empty 덮어쓰기 (총 178 통과, v0.4.0 의 174 + 4)

### Verified (실 Anthropic API 평가)

worklog/011 § 9 의 5개 합격 기준 모두 통과:

| 기준 | 합격선 | 실측 |
|---|---|---|
| caption 한국어 비율 | ≥ 30% | **67%** |
| image_type 정확도 | ≥ 4/5 | **4/5 (80%)** ※ 오답 1건은 합성 픽스처 한계 |
| auto_approved 비율 (conf ≥ 0.7) | 60-80% | **100%** (다양성 부족 — 모두 ≥0.92) |
| 이미지당 비용 | ≤ $0.01 | **$0.0027** (합격선의 1/4) |

- 합성 5건 평가 비용 총 18.75원 ($0.0136), wall time 20.4초
- 2-pass 트리거 0/5 (Sonnet confidence 가 모두 ≥0.92 → 임계값 0.7 효과 미검증)
- v0.4.1 baseline: `worklog/013` § 2-3 의 표

### Quality gates (실측)

- pytest: **178 통과** (v0.4.0 의 174 + 4 dotenv)
- 전체 라인 커버리지: **91%+** (v0.4.0 동일)
- ruff + mypy strict + pre-commit: 모두 통과
- 실 API 호출 5건 (평가) + mock 53건 = 모두 안정

### Deferred to v0.5 (Pipeline + PostgreSQL)

- 변동 없음 — worklog/011 § 8 + worklog/013 § 5-2 권고 patch 우선

### Recommended v0.4.x patches (worklog/013 § 5-2)

- v0.4.2: 실 PDF/PPTX 이미지 N=10 평가 (합성 한계 보완)
- v0.4.3: Haiku 비교 측정 (비용 1/10 가능 여부)
- v0.4.4: `kdp-label stats` 명령 (캐시 적중률 / 일별 비용)

---

## [0.4.0] — 2026-05-24

**Minor — public API 추가.** `kdp-label` Vision CLI 신설.
SemVer minor: 새 CLI entry point + `[vision]` 옵트인 extras. `__init__.py` 노출
항목 변동 없음. 코어 사용자 영향 0 (extras 안 깔면 vision 모듈 미import).

v0.4 종합 의사결정 (20+ 항목) 은 `worklog/011_v0.4_decision_matrix.md` 참고.
실 API 평가 (worklog/012) 는 사용자 ANTHROPIC_API_KEY 보유 시 후속 작업.

### Added

- **`kdp-label` CLI** (`packages/core/src/korean_doc_parser/cli/label.py`):
  - 단일 이미지 모드: `kdp-label image.png` → JSON 1건 (stdout)
  - 문서 모드: `kdp-label --from-document doc.pdf` → JSONL (이미지 1건/줄)
  - Claude Sonnet (worklog/011 A.1) + 2-pass 라벨링 (B.1, confidence < 0.7 시
    reasoning 추가 호출)
  - 비트맵 ≥ `--min-px 100` (B.2), 한국어 caption (B.3), OCR 없음 (B.4)
  - caption + reasoning post-process PII 마스킹 (C.2 — 주민번호/전화/이메일)
  - SQLite `sha256 + model` 캐시 (C.4, `--cache-path` 옵션, default `~/.kdp-cache.db`)
  - cost_krw / input_tokens / output_tokens / cache_hit / second_pass 등 모든
    Vision usage 메타 출력 (A.4 — v0.5 PostgreSQL cost_log 의 직전 단계)
- **`vision/` 패키지** (`packages/core/src/korean_doc_parser/vision/`):
  - `client.py` — Anthropic SDK wrapper + 2-pass + 캐시 통합
  - `cache.py` — SQLite `vision_cache` 테이블 + stats
  - `mask.py` — Korean PII regex (주민번호 / 전화 / 이메일)
  - `pricing.py` — Haiku/Sonnet/Opus 가격표 + cache_read 90% 할인 + cache_creation 125%
  - `prompts.py` — 한국어 system prompt (1-pass / 2-pass)
- **새 의존성:** `anthropic>=0.40` (extras `[vision]`, MIT, ~1MB)
- **새 entry point:** `kdp-label = korean_doc_parser.cli.label:main`

### Quality gates (실측)

- pytest: **174 통과** (v0.3.0 의 121 + 신규 53 vision/CLI mock 테스트)
- 전체 라인 커버리지: **91.03%** (게이트 85% + 마진 ~6%p)
  - `vision/cache.py` / `mask.py` / `pricing.py` / `prompts.py`: 100%
  - `vision/client.py`: 98% (lazy import 분기 미커버)
  - `cli/label.py`: 56% (실 API 호출 path 는 worklog/012 평가에서 자연 커버)
- ruff + mypy strict + pre-commit: 모두 통과
- mock Anthropic SDK 로 단위 테스트 (실 API 호출 0건, 비용 0원)

### Deferred to v0.5 (Pipeline + PostgreSQL)

- DocumentIngestionPipeline (검수 큐 상태 머신: pending → ... → user_approved)
- PostgreSQL 6 테이블 (cost_log / image_label_cache / review_queue / history /
  retry_queue / users-옵션) — v0.4 SQLite 캐시는 schema 호환되게 마이그
- 비동기 worker (D.2)
- doc_id = sha256(file) 멱등성 (D.3) + 부분 실패 시 롤백 (D.4)

### Pending evaluation (worklog/012)

- 실 PPTX/PDF 의 추출 이미지 N≥5 로 Vision 호출 → caption 품질 / cost / Haiku 비교
- ANTHROPIC_API_KEY 보유 사용자가 v0.4.x patch 로 worklog/012 채움
- 결과에 따라 v0.5 진입 전 모델 / 임계값 / 라벨링 범위 재조정 가능

### Deferred to v0.5 (Pipeline + PostgreSQL)

- DocumentIngestionPipeline (검수 큐 상태 머신: pending → ... → user_approved)
- PostgreSQL 6 테이블 (cost_log / image_label_cache / review_queue / history /
  retry_queue / users-옵션)
- 비동기 worker (D.2)
- doc_id = sha256(file) 멱등성 (D.3) + 부분 실패 시 롤백 (D.4)

### Deferred to v0.6 (검수 UI)

- FastAPI + HTML/JS 검수 UI
- 신뢰도 낮은 순 정렬 (E.2)
- 1인 권한 (E.4), 다인은 v0.7+
- F 카테고리 (UI 기술 / 배포 / 단축키) 의 본격 결정

### Deferred to v0.7+ or later

- Active Learning (E.3 진입) — few-shot 또는 fine-tune
- 다인 검수 / 워크플로우 (E.4 확장)
- 도형/차트 라벨링 (B.2 비트맵만 → PyMuPDF [pdf-render] extras 검토)
- 영문 caption (B.3 한국어 only → 병기 patch)
- HWP 이미지 추출 (XHTML `bindata/` 경로 → `ExtractedImage`)
- HWP 회귀 시간 30초 목표 (pytest-xdist 병렬화)
- PPTX 표 → `ParsedTable[]` 승격, PPTX 이미지 placeholder → `ExtractedImage` 비트맵 추출
- OOXML 차트 데이터, 캡션 정제

---

## [0.3.0] — 2026-05-24

**Minor — public API 추가.** PPTX 1포맷 추가 (markitdown 위임). SemVer minor:
`extract(...)` 가 처리하는 확장자 4종(`.docx/.hwp/.hwpx/.pdf`) → 5종(+`.pptx`).
`__init__.py` 노출 항목 변동 없음.

**정책 변경 (2026-05-24):** LibreOffice 도입 영구 금지로 v0.3 scope 가 DOC/PPT/PPTX
3포맷에서 PPTX 1포맷으로 축소되었습니다. 최종 지원은 **5포맷** (7포맷 목표 폐기).
의사결정 / 출시 잠재 과제는 `worklog/009_no_libreoffice_decision.md` /
`worklog/010_v0.3.0_release.md` 참고.

### Added

- **PPTX 파서** (`korean_doc_parser.parsers.pptx.PptxParser`, markitdown 위임):
  - `pip install korean-doc-parser[pptx]` 옵트인 — markitdown[pptx] 의 80MB ML 스택
    (`onnxruntime` + `numpy` + `magika`) 은 PPTX 안 쓰는 사용자에게 영향 0
  - markitdown 의 슬라이드별 `<!-- Slide number: N -->` 마커 보존 — 다운스트림
    RAG 청킹 시 슬라이드 단위 분할 가능
  - 표/이미지는 markdown 본문에 인라인 (`| --- |` 표 형식, `![](file.png)` 이미지
    placeholder) — `ParsedTable[]` / `ExtractedImage[]` 승격은 v0.4+
  - 평가: 실 PPTX 7건 + 합성 4건 = 11건 중 정상 7/7 통과 + 깨진 1건 정상 ParseError
- **벤치마크 어댑터 확장** — `KoreanDocParserAdapter.supported_formats()` 에 `.pptx`
  추가 (markitdown 가용 시)
- **새 의존성:** `markitdown[pptx]>=0.1.5` (extras `[pptx]`, MIT, 80MB transitive
  with python-pptx) — Python 패키지 boundary 만 유지 (worklog/009 § 3 정합)

### Quality gates (실측)

- pytest: **121 통과** (v0.2.1 의 104 + 신규 17)
- 전체 라인 커버리지: **95.34%** (게이트 85% + 마진 ~10%p)
  - `core.py` / `exceptions.py`: 100%
  - `parsers/pdf.py`: 95%, `parsers/docx.py`: 97%, `parsers/hwpx.py`: 96%
  - `parsers/pptx.py`: **86%** (markitdown ImportError / title 추출 실패 분기 미커버 — 의도적)
  - `korean_doc_parser_hwp/parser.py`: 93%
- ruff + mypy strict + pre-commit: 모두 통과
- 회귀 시간: ~4분 16초 (HWP 5건 + PPTX 7건 + 합성 모두). v0.4 patch 후보로
  pytest-xdist 검토

### Performance (markitdown PPTX 평가)

| 픽스처 | slides | md_len | 처리 시간 |
|---|---|---|---|
| 한국관광공사 제안서 | 37 | 23K | 0.4초 |
| lets_portal tmp | 42 | 39K | 0.7초 |
| QVAN 스토리보드 (최대) | **142** | **113K** | **2.5초** |

end user 응답 시간 합리적 (< 10초). 합성 4건은 모두 0.1-0.2초.

### Deferred to v0.4 or later

- Pipeline 패키지 — DocumentIngestionPipeline + Claude Vision 라벨링 + 검수 큐
- 검수 UI (FastAPI + HTML)
- HWP 이미지 추출 (XHTML `bindata/` 경로 → `ExtractedImage`)
- HWP 회귀 시간 30초 목표 (pytest-xdist 병렬화)
- PPTX 표 → `ParsedTable[]` 승격 (현재는 markdown 본문에 인라인만)
- PPTX 이미지 placeholder → `ExtractedImage` 비트맵 추출 (Vision 라벨링과 동기)
- Active Learning + 캡션 정제 + OOXML 차트 데이터

---

## [0.2.1] — 2026-05-22

**Patch — public API 무변경.** HWP 5건 픽스처 회귀 시간 단축. SemVer patch
(`__init__.py` 노출 함수·클래스·타입 동일, 동작 변경 없음).

자세한 의사결정은 `worklog/008_v0.2.1_release.md` 참고.

### Changed

- **HWP 픽스처 fixture 2단 분리** (`packages/hwp/tests/conftest.py`):
  - 기존: `hwp_<name>` 가 `Path` 만 반환 → 각 테스트가 매번 `extract()` 재호출.
    `test_nara` 가 3개 테스트에서 사용되어 3번 파싱 (150초 낭비)
  - 변경: `hwp_<name>` (Path) + `hwp_<name>_result` (`ParseResult`, session-scoped)
    이중 fixture. 각 HWP 1회만 파싱, 결과는 세션 내 모든 테스트가 공유

### Quality gates (실측)

- pytest: **104 passed** (수치 동일, 회귀 시간만 단축)
- 전체 라인 커버리지: 95.96% (v0.2.0 동일)
- **HWP 회귀 시간: 5분 53초 → 1분 59초 (66% 단축)**
- ruff + mypy strict + pre-commit: 모두 통과

---

## [0.2.0] — 2026-05-22

**Minor — public API 추가.** HWP 5.x 파서 + PDF 비트맵 실 추출. SemVer minor:
`korean_doc_parser/__init__.py` 의 노출 항목은 변경 없음, 단 `extract(...)`
가 처리하는 확장자가 `(.docx, .hwpx, .pdf)` → `(.docx, .hwp, .hwpx, .pdf)` 로 확장.

의존성 매트릭스 결정의 표면/진짜 근거는 `worklog/006_v0.2_dependency_matrix.md`,
출시 의사결정 / 잠재 과제는 `worklog/007_v0.2.0_release.md` 참고.

### Added

- **HWP 파서** (`korean_doc_parser_hwp.HwpParser`, `pyhwp` 기반):
  - `packages/hwp/` 격리, 자동 등록 — `import korean_doc_parser_hwp` 만 하면
    `korean_doc_parser.extract(...)` 가 `.hwp` 를 처리
  - pyhwp 의 `HTMLTransform` → XHTML → BeautifulSoup 로 마크다운 + ParsedTable 분리
  - 실 픽스처 5건 통과 — 도메인 다양성(인천/원광대/경남귀어/산림/창업), 크기
    228 KB ~ 22 MB 범위, 표 47 ~ 90건. `samples/` 는 git untracked, 픽스처 미존재 시
    `pytest.skip` 가드
  - lets_portal 1차 작업(`_parse_hwp_pyhwp` + `_xhtml_to_markdown`) 의 모듈화 이전
- **PDF 비트맵 실 추출** (`korean_doc_parser.parsers.pdf`, `pypdf` 추가):
  - v0.1.0 의 `ExtractedImage.file_path` / `sha256` placeholder 제거 — 실 tempfile +
    sha256 + width/height/size_bytes/mime_type 모두 실값으로 채워짐
  - pdfplumber bbox + pypdf bitmap 의 per-page 인덱스 매칭 (count 불일치 시 방어 fallback)
  - 합성 픽스처 3건 추가 — JPEG (`/DCTDecode`), CMYK JPEG, multi-page multi-image
- **새 의존성:**
  - `pypdf>=4.0` (core, BSD-3, ~2MB)
  - `pyhwp>=0.1b15` (extras `[hwp]`, **AGPLv3+** — 사내 라이브러리 사용에 영향 없음, 격리 유지)
  - `six>=1.16`, `beautifulsoup4>=4.12`, `lxml>=5.0` (`[hwp]` extras transitives)
- **벤치마크 어댑터** — `benchmarks/adapters/kdp_adapter.py`. v0.2.0 시점 self-baseline
  결과는 `benchmarks/results/v0.2.0_baseline.{json,md}` 에 보존. 향후 patch 의
  CLAUDE.md §"라이브러리 특화 규칙 §6" `±5%` 비교 기준점.

### Changed

- **`packages/hwp/pyproject.toml` license 정정** — `GPL-3.0-or-later` → `AGPL-3.0-or-later`
  (pyhwp 실 라이선스 = AGPLv3+). 격리 전략 자체는 동일하게 작동.
- **mypy override** — `pyhwp.*` (잘못된 이름) → `hwp5.*` + `bs4.*` 추가
- **pytest pythonpath** — `packages/core` 추가, 공유 테스트 헬퍼 (`tests/_gt.py`,
  `tests/_synth.py`) 가 다른 패키지 테스트에서 import 가능

### Quality gates (실측)

- pytest: **104 통과** (v0.1.1 의 78 + 신규 26)
- 전체 라인 커버리지: **95.96%** (게이트 85% + 마진 ~11%p)
  - `core.py` / `exceptions.py`: 100%
  - `parsers/pdf.py`: 95%, `parsers/docx.py`: 97%, `parsers/hwpx.py`: 96%
  - `korean_doc_parser_hwp/parser.py`: 93%
- ruff lint + format + mypy strict + pre-commit (gitleaks 포함): 모두 통과
- 벤치마크 (9 fixtures, korean_doc_parser 어댑터): 9 ok / 0 errors, mean 52.9s,
  composite 0.910. `benchmarks/results/v0.2.0_baseline.json` 참조.

### Deferred to v0.3 or later

- LibreOffice 경유 4포맷(DOC/PPTX/PPT/이미지) — system 의존성 boundary 분리
- HWP COM 폴백 — pyhwp 단독 통과율 ≥ 90% 시 미진입 (현 픽스처 5/5 통과)
- HWP kordoc 포팅 — pyhwp 단독 통과율 ≤ 70% 시 진입
- HWP 이미지 추출 — XHTML 의 `bindata/` 경로를 `ExtractedImage` 로 승격
- PDF CCITTFax 픽스처 — reportlab 으로 합성 어려움, 실 스캔 PDF 픽스처 진입 시점에 추가
- HWP 5건 픽스처 회귀 시간 ~5분 — session-scoped 캐싱으로 최적화 여지

---

## [0.1.1] — 2026-05-22

**Patch — 공개 API 무변경.** 3포맷 마감 작업: HWPX 이미지 분기 픽스처 보강 +
coverage 85% 게이트 활성화. SemVer patch (`__init__.py` 노출 함수·클래스·타입 동일).

자세한 의사결정/잠재 과제는 `worklog/005_v0.1.1_release.md` 참고.

### Added

- HWPX 이미지 픽스처 3건 (`tests/_synth.py`):
  - `build_hwpx_with_image` — `BinData/image1.png` (32×32 PNG)
  - `build_hwpx_with_image_resources` — `Contents/Resources/image1.jpg` (48×24 JPEG)
  - `build_hwpx_with_image_corrupt` — `BinData/broken.bin` (PIL inspect 실패 → fallback)
- HWPX 이미지 테스트 6건 (`tests/test_hwpx_parser.py`):
  비트맵 추출 / 두 media-root 경로 / `_inspect_image` 예외 경로 / 각 GT 매칭

### Changed

- **coverage 85% 게이트 활성화** (`pyproject.toml` `[tool.coverage.report] fail_under = 85`).
  CLAUDE.md §"라이브러리 특화 규칙 §3" 의 "85% 미만 머지 금지" 의무를 자동 게이트로 제도화.
- HWPX 라인 커버리지 **83% → 96%** (이미지 추출 분기 도달).

### Quality gates (실측)

- pytest: **78 통과** (v0.1.0 의 72 + 신규 6)
- 전체 라인 커버리지: **97%** (v0.1.0 의 93% → +4%p)
  - `core.py` / `exceptions.py`: 100%
  - `parsers/pdf.py` 97% / `parsers/docx.py` 97% / `parsers/hwpx.py` **96%**
- ruff + mypy strict + pre-commit: 모두 통과
- `fail_under = 85` 게이트: 통과 (마진 12%p)

### Deferred to v0.2 (v0.1.0 의 미해결 항목 중)

- PDF 이미지 비트맵 추출 — `pypdf` 신규 의존 vs pdfplumber 내부 stream 직접 처리.
  v0.2 HWP/LibreOffice 작업과 함께 의존성 매트릭스 종합 검토.

---

## [0.1.0] — 2026-05-21

**최초 사내 릴리즈.** PDF / DOCX / HWPX 3포맷을 마크다운 + 표 + 이미지 +
메타데이터로 변환하는 사내 private 라이브러리.

scope 결정 이력: 원래 v0.1 합격 기준은 7포맷이었으나, 외부 환경 의존성
(pyhwp / LibreOffice / 한·글 COM) 이 큰 4포맷(HWP/DOC/PPT/PPTX) 을 v0.2 로
분리. 자세한 의사결정은 `worklog/002_v0.1.0_release.md` 참고.

### Added

- 모노레포 부트스트랩 — `uv workspace` + 3 패키지 (`core` / `hwp` / `pipeline`)
- 린트 / 타입 / 테스트 설정 (`ruff` + `mypy strict` + `pytest` + `coverage`)
- pre-commit hook (`ruff`, `mypy`, `gitleaks`, 기본 위생)
- GitHub Actions CI:
  - lint-and-test × (Ubuntu + Windows) × Python 3.11
  - integration (LibreOffice on Ubuntu, `-m slow` 마커) — v0.2 에서 본격 활용
- 한국어 `README.md` 작성
- Git 운영 규칙 명문화 — Conventional Commits + commit 마다 push (CLAUDE.md §"Git 운영")
- **`korean_doc_parser` public API 첫 정의** (SemVer 의무 시작점):
  - 데이터 타입: `ParseResult`, `ExtractedImage`, `ParsedTable`, `ParseMetadata`
    (모두 `frozen=True, slots=True` dataclass)
  - `BaseParser` ABC + `ParserRegistry` (확장자 → 파서 플러그인 패턴)
  - 함수: `extract(path)`, `register_parser(parser)`, `get_parser(ext)`,
    `supported_extensions()`
  - 예외: `KoreanDocParserError`, `UnsupportedFormatError`, `ParseError`
- **PDF 파서** (`korean_doc_parser.parsers.pdf.PdfParser`, pdfplumber 기반):
  - 텍스트(페이지별), 표(pdfplumber 디폴트 휴리스틱), 이미지 메타데이터 추출
  - 자동 등록 — `import korean_doc_parser` 시 `.pdf` 즉시 사용 가능
  - 메타데이터: `page_count`, `title`, `author` (bytes/str/None 안전 변환)
  - 합성 픽스처 4건 (simple / multipage / with_table / with_image), 라인 커버리지 97%
- **DOCX 파서** (`korean_doc_parser.parsers.docx.DocxParser`, python-docx 기반):
  - 텍스트(`Heading 1` / `제목 1` 등 → ``#`` 마크다운 헤더 변환)
  - 표(`doc.tables` → `ParsedTable[]`)
  - 이미지(ZIP 안 `word/media/*` 직접 추출 → tempfile + sha256, 비트맵 포함)
  - 메타데이터: `title`, `author`, `created_at`, `modified_at`
  - 합성 픽스처 3건 (simple / with_table / with_image), 라인 커버리지 97%
- **HWPX 파서** (`korean_doc_parser.parsers.hwpx.HwpxParser`, XML 직접 파싱):
  - namespace-agnostic 워크 — 한/글 실 schema + 합성 모두 호환
  - 텍스트(`<*:p>` paragraphs), 표(`<*:tbl>`), 이미지(`BinData/*` + `Contents/Resources/*`)
  - 메타데이터 `title`: `Contents/content.hpf` 의 `<opf:title>`
  - 합성 픽스처 2건 (simple / with_table), 라인 커버리지 83%

### Known limitations (v0.2 에서 해소 예정)

- **PDF 이미지 비트맵 미추출** — `ExtractedImage.file_path` / `sha256` 가 placeholder.
  pdfplumber 자체로는 비트맵 미제공 → 추가 의존성 필요. v0.2 에서 일관성 회복.
- **HWPX 이미지 픽스처 미포함** — 합성 어렵고 실 한/글 파일 의존성 회피.
  v0.2 에서 픽스처 추가로 라인 커버리지 95%+ 회복.
- **HWP / DOC / PPT / PPTX 4포맷 미지원** — v0.2 마일스톤. 자세한 이월 이유는
  `worklog/002_v0.1.0_release.md` 참고.

### Quality gates (실측)

- pytest: 72 통과 (PDF 14 / DOCX 12 / HWPX 13 / core 14 / fixtures infra 17 + parametrize 변형 2)
- 전체 라인 커버리지: **93%**
  - `core.py` / `exceptions.py`: 100%
  - `parsers/pdf.py`: 97%, `parsers/docx.py`: 97%, `parsers/hwpx.py`: 83%
- ruff lint + format + mypy strict: 모두 통과
- pre-commit (gitleaks 포함): 모두 통과

### Phase 0 산출물 (이미 commit 됨, 참조용)

- 경쟁 라이브러리 벤치마크 프레임워크 (markitdown / docling / marker / unstructured / legacy)
- 6건 샘플 벤치마크 결과 (`benchmarks/results/phase0_*.{json,md}`)
- 포맷별 위임/자체 결정 (`worklog/001_phase0_benchmark_decision.md`)
