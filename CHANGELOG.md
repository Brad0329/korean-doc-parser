# Changelog

이 프로젝트의 모든 주목할 만한 변경사항을 이 파일에 기록합니다.

형식은 [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/) 을 따르고,
버전은 [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html) 을 준수합니다.

**SemVer 의무 (CLAUDE.md §"라이브러리 특화 규칙 §1"):**
public API (`korean_doc_parser/__init__.py` 노출 함수·클래스·타입) 변경 시
patch / minor / major 판단을 PR 본문 또는 commit 메시지에 명시합니다.

---

## [Unreleased]

### Added (Phase 1 빌드)

- 모노레포 부트스트랩 — `uv workspace` + 3 패키지 (`core` / `hwp` / `pipeline`)
- 린트 / 타입 / 테스트 설정 (`ruff` + `mypy strict` + `pytest` + `coverage`)
- pre-commit hook (`ruff`, `mypy`, `gitleaks`, 기본 위생)
- GitHub Actions CI:
  - lint-and-test × (Ubuntu + Windows) × Python 3.11
  - integration (LibreOffice on Ubuntu, `-m slow` 마커)
- 한국어 `README.md` 작성, `CHANGELOG.md` 초기 작성
- Git 운영 규칙 명문화 — Conventional Commits + commit 마다 push
- **`korean_doc_parser` public API 첫 정의** (SemVer 의무 시작점):
  - 데이터 타입: `ParseResult`, `ExtractedImage`, `ParsedTable`, `ParseMetadata`
    (모두 `frozen=True, slots=True` dataclass)
  - `BaseParser` ABC + `ParserRegistry` (확장자 → 파서 플러그인 패턴)
  - 함수: `extract(path)`, `register_parser(parser)`, `get_parser(ext)`,
    `supported_extensions()`
  - 예외: `KoreanDocParserError`, `UnsupportedFormatError`, `ParseError`
  - 단위 테스트 14건, 커버리지 100% (`core.py` + `exceptions.py`)
- **PDF 파서** (`korean_doc_parser.parsers.pdf.PdfParser`, pdfplumber 기반):
  - 텍스트(페이지별), 표(pdfplumber 디폴트 휴리스틱), 이미지 메타데이터 추출
  - 자동 등록 — `import korean_doc_parser` 시 `.pdf` 가 즉시 사용 가능
  - 메타데이터: `page_count`, `title`, `author` (bytes/str/None 안전 변환)
  - **알려진 제약 (v0.2 에서 해소):** 이미지 비트맵 바이트 미추출 —
    `ExtractedImage.file_path` / `sha256` 가 placeholder
  - 합성 픽스처 4건 (simple / multipage / with_table / with_image) +
    테스트 14건, 라인 커버리지 97%

### Phase 0 산출물 (이미 commit 됨)

- 경쟁 라이브러리 벤치마크 프레임워크 (markitdown / docling / marker / unstructured / legacy)
- 6건 샘플 벤치마크 결과 (`benchmarks/results/phase0_*.{json,md}`)
- 포맷별 위임/자체 결정 (`worklog/001_phase0_benchmark_decision.md`)

---

## v0.1.0 출시 시점에 [Unreleased] → [0.1.0] 으로 이동 예정.

v0.1.0 합격 기준 (HANDOVER §6):

- [ ] 7포맷 모두 텍스트 + 표 + 이미지 + 메타데이터 추출 동작
- [ ] LibreOffice 변환 경로(DOC→DOCX, PPT→PPTX) 픽스처 각 최소 5건 통과
- [ ] pytest 커버리지 85%+
- [ ] CI 통과 (Ubuntu + Windows × Python 3.11)
- [ ] README.md / CHANGELOG.md 갱신
