# Changelog

이 프로젝트의 모든 주목할 만한 변경사항을 이 파일에 기록합니다.

형식은 [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/) 을 따르고,
버전은 [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html) 을 준수합니다.

**SemVer 의무 (CLAUDE.md §"라이브러리 특화 규칙 §1"):**
public API (`korean_doc_parser/__init__.py` 노출 함수·클래스·타입) 변경 시
patch / minor / major 판단을 PR 본문 또는 commit 메시지에 명시합니다.

---

## [Unreleased]

(다음 마일스톤은 v0.4 — Pipeline 패키지 + Claude Vision 라벨링. worklog/010 § 6 참고.)

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
