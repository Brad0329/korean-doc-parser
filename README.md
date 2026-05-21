# korean-doc-parser

> HWP/HWPX 를 포함한 한국어 문서를 마크다운 + 이미지 + 메타데이터로 변환하는 **사내 private 라이브러리**.

**상태:** Phase 1 빌드 중 (v0.1.0 출시 예정). 아직 정식 릴리즈 없음.

---

## 왜 이 라이브러리인가

markitdown / marker / docling 같은 글로벌 마크다운 변환기는 한국 문서의 핵심 포맷인 **HWP/HWPX** 를 지원하지 않습니다. `korean-doc-parser` 는 그 빈 영역을 채우는 사내 라이브러리로,

- **7포맷 지원:** HWP / HWPX / PDF / DOCX / DOC / PPTX / PPT
- **2계층 아키텍처:** 순수 추출 엔진(`core`/`hwp`) + AI 라벨링/검수 파이프라인(`pipeline`)
- **단일 파일 포터빌리티:** 코어는 외부 import 0건 — 다른 프로젝트에 단일 패키지로 도입 가능
- **5종 한국 도메인 타깃:** 입찰공고 / 법률검토 / 공문 / 전람회 PDF / 제안서

---

## 패키지 구조

| 패키지 | 라이선스 | 설명 |
|---|---|---|
| `korean-doc-parser` | MIT | 메인 엔진 (PDF/DOCX/HWPX/PPTX/PPT/DOC) |
| `korean-doc-parser-hwp` | GPL-3.0-or-later | HWP 파서 (pyhwp 의존, 격리) |
| `korean-doc-parser-pipeline` | MIT | AI 라벨링 + 검수 큐 (Claude Vision) |

```
korean-doc-parser/
├── packages/
│   ├── core/          ← pip install korean-doc-parser
│   ├── hwp/           ← pip install korean-doc-parser-hwp
│   └── pipeline/      ← pip install korean-doc-parser-pipeline
├── benchmarks/        ← 경쟁 라이브러리 비교 (Phase 0 산출물)
├── worklog/           ← 마일스톤·의사결정 기록
└── docs/ko/           ← 사용자 문서 (v0.1.0 출시 시 작성)
```

---

## 포맷별 처리 전략 (Phase 0 결정)

| 포맷 | 구현 방식 | 위치 |
|---|---|---|
| **HWP** | 자체 구현 (pyhwp + 한/글 COM 폴백) | `packages/hwp` |
| **HWPX** | 자체 구현 (OOXML 유사 XML 직접 파싱) | `packages/core` |
| **PDF** | 자체 구현 (pdfplumber) — 표 인식 32개 vs markitdown 0개 | `packages/core` |
| **DOCX** | 자체 구현 (python-docx) — 속도 50배 우위 | `packages/core` |
| **DOC** | LibreOffice → DOCX 변환 후 자체 파서 | `packages/core` |
| **PPTX** | markitdown 위임 (text 23K vs 자체 170) | `packages/core` |
| **PPT** | LibreOffice → PPTX 변환 후 markitdown | `packages/core` |

자세한 의사결정 근거는 [`worklog/001_phase0_benchmark_decision.md`](worklog/001_phase0_benchmark_decision.md) 참고.

---

## 설치 (사내 사용)

> v0.1.0 출시 전까지는 git 직접 설치만 지원.

```bash
# 코어만
pip install "git+https://github.com/Brad0329/korean-doc-parser.git#subdirectory=packages/core"

# HWP 포함
pip install "git+https://github.com/Brad0329/korean-doc-parser.git#subdirectory=packages/hwp"

# 풀세트 (AI 라벨링까지)
pip install "git+https://github.com/Brad0329/korean-doc-parser.git#subdirectory=packages/pipeline"
```

---

## 사용 예시

> ⚠️ Phase 1 빌드 중 — 아래 API 는 v0.1.0 출시 시점의 예상 형태입니다.

```python
from korean_doc_parser import extract

result = extract("계약서.hwp")

print(result.markdown)          # 마크다운 본문
print(result.metadata.format)   # "hwp"
print(len(result.tables))       # 표 개수

for img in result.images:
    print(img.page_no, img.detected_caption, img.sha256)
```

검수 파이프라인까지:

```python
from korean_doc_parser_pipeline import DocumentIngestionPipeline

pipeline = DocumentIngestionPipeline(api_key=...)
result = pipeline.ingest("제안서.pdf")

for img in result.images:
    print(img.ai_caption, img.ai_confidence, img.status)
    # status = auto_approved | needs_review
```

---

## 개발 환경

이 repo 는 [uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/) 로 관리합니다.

```bash
# clone 후 1회 셋업
uv sync                              # 의존성 설치
uv run pre-commit install            # git hook 등록

# 일상 작업
uv run pytest                        # 테스트
uv run ruff check .                  # 린트
uv run ruff format .                 # 포맷
uv run mypy                          # 타입 체크 (strict)
uv run pre-commit run --all-files    # 전체 훅 수동 실행
```

작업 규칙 (Git Conventional Commits / commit 게이트 / 라이브러리 SemVer 등) 은
[`CLAUDE.md`](CLAUDE.md), 프로젝트 컨텍스트는 [`HANDOVER.md`](HANDOVER.md) 를 참고하세요.

---

## 라이선스

- **코어 / 파이프라인** (`packages/core`, `packages/pipeline`): **MIT** — [`LICENSE`](LICENSE)
- **HWP extras** (`packages/hwp`): **GPL-3.0-or-later** — [`packages/hwp/LICENSE`](packages/hwp/LICENSE)

HWP 패키지가 pyhwp (GPL v3) 의존성 때문에 GPL 격리되어 있습니다.
HWP 를 쓰지 않으면 MIT 만으로 충분합니다.

---

## 슬로건

> **"HWP-aware document-to-markdown library for Korean documents.**
> A markitdown alternative with native HWP/HWPX support."
