# Changelog

이 프로젝트의 모든 주목할 만한 변경사항을 이 파일에 기록합니다.

형식은 [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/) 을 따르고,
버전은 [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html) 을 준수합니다.

**SemVer 의무 (CLAUDE.md §"라이브러리 특화 규칙 §1"):**
public API (`korean_doc_parser/__init__.py` 노출 함수·클래스·타입) 변경 시
patch / minor / major 판단을 PR 본문 또는 commit 메시지에 명시합니다.

---

## [Unreleased]

(다음 마일스톤은 v0.2 — HWP / PPTX / PPT / DOC 추가. worklog/002 참고.)

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
