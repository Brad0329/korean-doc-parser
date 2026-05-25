# Known limitations — `korean-doc-parser` v0.5.0 시점 살아있는 잠재 과제

> **독자:** 메인테이너 / 미래 메인 agent 세션 / bidwatch 운영자
> **갱신 시점:** v0.5.0 release (2026-05-25)
> **출처:** worklog/011 ~ 020 의 § "잠재 과제 / 다음 세션이 알아야 할 것" 통합

이 문서는 v1.0 stable lock 시점에 **여전히 살아있는** 잠재 과제만 모은
단일 진실원입니다. 처리된 항목은 `archive/worklog/` 에 그대로 보존
(git history 유지). 새 잠재 과제가 v1.0+ 에서 발견되면 이 파일에 추가하고
worklog 에도 박는 패턴 유지.

---

## A. 운영 진입 전 검증 권고 (호출자 / bidwatch 영향)

### A-1. BMP 의 Claude Vision API 호환성 미검증

**출처:** `worklog/017 § 4-3`

HWP 의 `bindata/` 가 PNG / JPEG **+ BMP** 를 emit. Vision API 가 BMP 를 직접
지원하는지 미검증. 거부 시 `kdp-label` 호출에서 4xx 발생 가능.

- **검증 방법:** 단일 BMP 이미지로 `kdp-label sample.bmp` 1회 호출 (약 1원)
- **거부 시 대응 (v0.4.6 또는 v0.5.x patch 후보):** parsers/_imageutil.py 또는
  VisionClient 에서 BMP → PNG 변환 후 호출 (PIL 로 변환 5줄)
- **bidwatch 운영 진입 전 필수 검증** — 검증 안 하면 HWP 처리 실패 발생 가능성

### A-2. default 모델 Haiku 전환 (v0.5.0 의 동작 변경)

**출처:** `worklog/014 § 4-2`, `worklog/020 § 4-2`

CLI / Python API 의 default 가 Sonnet → Haiku. **호출자 코드 변경 0건**이지만
운영 시작 후 비용 / 품질 차이 모니터링 권고:

- 비용 약 1/10.6 감소 (worklog/014 의 22건 실측)
- 한국어 caption 품질 동등 (93% / 93%)
- confidence calibration 이 더 정직 (검수 큐 정렬 가능)
- 정밀 필요 케이스: `--model claude-sonnet-4-5` 명시

---

## B. v1.0 이후 patch 후보 (호출자 가치 발생 시 진입)

### B-1. PPTX 의 chart / smartart 미지원

**출처:** `worklog/016 § 4-2`

현재 `MSO_SHAPE_TYPE.PICTURE` 만 추출. PPTX 안 chart / smartart 는 별도 XML
구조라 PNG 로 직접 렌더링 안 됨.

- **금지 대안:** LibreOffice 변환 (CLAUDE.md §"금지 의존성" 영구 차단)
- **잠재 경로:** matplotlib 자체 렌더링 / slide 전체를 PNG 로 렌더링
- **진입 조건:** bidwatch 가 실제 chart-only PPTX 처리 필요해질 때

### B-2. HWP 이미지의 `page_no` / `bbox` 복원

**출처:** `worklog/017 § 4-1`

현재 HWP 의 `ExtractedImage.page_no` / `bbox` 모두 None. proximity caption 검출
불가, 호출자가 페이지 정보로 필터링 불가.

- **이론적 경로:** pyhwp 의 record-level 접근 (`bodytext/section*.xml` 의
  paragraph 단위 picture anchor)
- **난이도:** HWP 의 layout-driven 페이지네이션은 렌더 시점에 결정 → 정확한
  page_no 보존 비자명
- **진입 조건:** bidwatch 가 HWP 의 페이지 정보 요구

### B-3. caption 1차 검출의 각 파서 자동 통합

**출처:** `worklog/020 § 5-1`

v0.5.0 시점에는 알고리즘 모듈 (`korean_doc_parser.pipeline.caption`) 만 박힘.
각 파서가 ExtractedImage 채울 때 자동 호출하는 통합은 미진입.

- **현재 호출자 패턴:**
  ```python
  cap, score = detect_caption_regex(img.text_before + "\n" + img.text_after)
  ```
- **자동 통합 (v0.6+):** pdf.py / docx.py / pptx.py 가 `_collect_*` 안에서
  caption 호출 → ExtractedImage 의 `detected_caption` / `caption_method` /
  `caption_pattern_score` 자동 채움
- **현재 진입 안 한 이유:** 각 파서마다 text-layout 패스가 달라서 통합 시점에
  파서별 결정 필요. v0.5.0 의 알고리즘 박는 단계와 분리

### B-4. bbox_unit 통일 정규화

**출처:** `worklog/016 § 4-3`, `worklog/020 § 5-2`

`ExtractedImage.bbox_unit` 이 px / emu / none. 호출자가 단위 일관성 책임
(같은 단위만 묶어서 `detect_caption_proximity` 호출).

- **자동 정규화 후보 (v1.0+):**
  - px 로 통일 (EMU → 96 DPI 가정 변환)
  - 슬라이드 크기 대비 비율 (0.0-1.0)
- **현재 진입 안 한 이유:** PPTX 의 slide 크기에 따라 변환 결과 다름,
  loseless 가 아님

### B-5. 같은 sha256 이미지의 중복 추출 (PPTX/PDF)

**출처:** `worklog/016 § 4-1`, `worklog/014 § 5-2`

엔진은 dedup 안 함. PPTX 의 qvan_storyboard 가 50 unique × 평균 10 슬라이드 =
499 ExtractedImage. CLI 만 쓰면 같은 이미지 N회 라벨 (cache hit 2회차 이후
0원이지만 row 증가).

- **라이브러리 정책 (worklog/019 § A.4):** 데이터 객체 반환만, dedup 은
  호출자 책임
- **호출자 측 dedup:** sha256 으로 묶어서 한 번만 Vision 호출 → DB 에는
  여러 page_no 로 N row

---

## C. 알고리즘 정밀화 (실 운영 데이터 누적 후 재검토)

### C-1. caption regex 패턴 정밀화

**출처:** `worklog/019 § 6-2`

현재 8 패턴 (한국어 4 + 영문 3 + 출처 1). samples 5종 도메인에서 결정.

- **확장 필요 가능 패턴:**
  - 표/그림 외 추가 (`<도표 N>` 일부 포함, `<수식 N>` 등)
  - 출처 변형 (`출처: `, `자료원: `, `Note: `)
  - 다국어 혼용 (`Figure 1 (그림 1)`)
- **검증 데이터:** bidwatch 운영 중 실 공고/제안서 누적

### C-2. 3중 가중 `weights` 의 실 운영 검증

**출처:** `worklog/019 § 6-3`

default `(0.4, 0.2, 0.4)` — worklog/011 § B 가설.

- **검증 방법:** 호출자가 다양한 weights 로 confidence 결과 비교 (수동 검수
  대비 ground truth)
- **HWP usecase 특화:** bbox=None → proximity weight 0, redistribute 패턴
  (worklog/020 § 5-1 의 예시)

### C-3. confidence 임계값 0.7 재검토

**출처:** `worklog/014 § 6-2`

worklog/014 의 22건 실측:
- Sonnet: 100% confidence ≥ 0.7 (calibration 평탄화) → 임계값 무용
- Haiku: 86.4% ≥ 0.7 (calibration 작동) → 임계값 의미 있음

→ default Haiku 전환 (v0.5.0) 후엔 0.7 유효. **운영 데이터 누적 시 0.85 /
0.9 같은 값 재검토 가능성**.

---

## D. 측정 / 게이트 정밀화

### D-1. ±5% 회귀 게이트의 노이즈 민감성

**출처:** `worklog/018 § 4-3`

CLAUDE.md §"라이브러리 특화 규칙 §6" 의 ±5% 룰. 단일 측정 + 시스템 부하 변동
영향 큼. v0.4.5 측정에서 21% 변동이 노이즈 영역으로 해석됨.

- **개선 (v1.0+):** N회 반복 측정 + 중앙값 / sigma 기반 게이트
- **CI 표준화:** 같은 PC / 같은 부하 조건 보장 (사내 CI runner)

### D-2. `benchmarks/adapters/` 의 PPTX 미반영

**출처:** `worklog/018 § 4-1`

v0.4.5 측정에서 13 fixtures 중 4 PPTX skip (adapter 가 v0.3 의 PPTX 지원
미반영). PPTX 의 회귀 측정 누락.

- **처리:** `benchmarks/adapters/korean_doc_parser.py` 의 `supported_extensions`
  에 `.pptx` 추가 후 재측정
- **v1.0 전 권고:** v1.0 baseline 박을 때 PPTX 포함된 13 fixtures 측정

### D-3. cache `hit_rate` 의 추세 분석

**출처:** `worklog/020 § 5-3`

v0.5.0 의 `stats()` 가 `hit_rate = total_hits / (total_hits + total_rows)` 반환.
누적 절대값이라 의미 제한적.

- **개선 (v0.6+):** `by_date` 에 `hit_count` 추가 → 일별 추세
- **운영 권고:** operator 가 `--stats` 를 주기적으로 호출해 추세 모니터링

---

## E. 도구 / 자동화 후보

### E-1. `samples/*.gt.json` 의 expected_image_count 자동 갱신

**출처:** `worklog/016 § 4-4`, `worklog/017 § 4-5`

`samples/` 는 `.gitignore`. 사용자 로컬의 ground truth 가 outdated 면 회귀
테스트 실패. v0.4.4 (PPTX) / v0.4.5 (HWP) 에서 측정값으로 수동 갱신.

- **자동화 (v1.0+):** `scripts/refresh_gt.py` — extract 결과로 expected_*
  필드 갱신, `_v{version}_note` 박음
- **사용 시점:** 새 PC 에서 samples 받았을 때 / 회귀 발생 시 인텐션 검증 후

### E-2. version 자동 bump 도구

**출처:** v0.4.x 누적 부채 (v0.4.2 → v0.4.5 동안 packages/core + hwp 의
pyproject.toml + __init__.py 가 stale 했던 사례)

- **현재 패턴:** release 마다 수동 4곳 (core/__init__.py, core/pyproject.toml,
  hwp/__init__.py, hwp/pyproject.toml) 갱신
- **자동화 후보:** `scripts/bumpversion.py` 또는 hatch-vcs / setuptools-scm
  도입
- **진입 조건:** release 빈도 늘어나면 가성비 있음

---

## F. 한 줄 요약

> **A 카테고리만 bidwatch 운영 진입 전 검증 필수** (BMP 호환성, 1원).
> B-F 는 모두 "호출자 가치 발생 시 진입" 또는 "운영 데이터 누적 후 재검토"
> — v1.0 stable lock 의 게이트 아님.

새 잠재 과제가 발견되면:
1. worklog/<번호>_<주제>.md 에 § "잠재 과제" 박음
2. 이 파일 (`docs/internal/known-limitations.md`) 에 해당 카테고리로 추가
3. 처리 완료 시 양쪽에서 제거 또는 "해소 (worklog/NNN)" 로 마킹
