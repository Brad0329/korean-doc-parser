# korean-doc-parser

> HWP / HWPX 를 포함한 한국어 문서를 마크다운 + 이미지 + 메타데이터로 변환하는 **사내 private 라이브러리**.

**상태:** **v0.2.1 출시** (2026-05-22). PDF / DOCX / HWP / HWPX 4포맷 지원.
PPTX 는 v0.3 으로 이월 (markitdown 위임). **DOC / PPT 는 영구 미지원**
(LibreOffice 도입 금지 결정 — `worklog/009_no_libreoffice_decision.md` 참고).

---

## 왜 이 라이브러리인가

markitdown / marker / docling 같은 글로벌 마크다운 변환기는 한국 문서의 핵심 포맷인 **HWP/HWPX** 를 지원하지 않습니다. `korean-doc-parser` 는 그 빈 영역을 채우는 사내 라이브러리로,

- **현재 v0.2.1:** PDF / DOCX / **HWP** / **HWPX** (4포맷)
- **v0.3 예정:** PPTX 1포맷 추가 → **5포맷 (최종)**
- **2계층 아키텍처:** 순수 추출 엔진(`core`/`hwp`) + AI 라벨링/검수 파이프라인(`pipeline`, v0.4+)
- **단일 파일 포터빌리티:** 코어는 외부 import 0건 — 다른 프로젝트에 단일 패키지로 도입 가능
- **boundary 1종 원칙:** 의존성은 Python 패키지만. system 의존성(LibreOffice 등) 영구 금지
- **5종 한국 도메인 타깃:** 입찰공고 / 법률검토 / 공문 / 전람회 PDF / 제안서

---

## 패키지 구조

| 패키지 | 라이선스 | 상태 | 설명 |
|---|---|---|---|
| `korean-doc-parser` | MIT | **v0.2.0** | 메인 엔진 (PDF / DOCX / HWPX, PPTX/PPT/DOC v0.3 이월) |
| `korean-doc-parser-hwp` | AGPL-3.0-or-later | **v0.2.0** | HWP 파서 (pyhwp 의존, 격리) |
| `korean-doc-parser-pipeline` | MIT | skeleton | AI 라벨링 + 검수 큐 (Claude Vision) — v0.4+ |

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

## 포맷별 처리 전략 (Phase 0 결정 + v0.2 갱신 + 2026-05-24 정책 반영)

| 포맷 | 구현 방식 | 위치 | 상태 |
|---|---|---|---|
| **HWP** | 자체 구현 (pyhwp 단독, COM 폴백 옵션) | `packages/hwp` | **v0.2.0** |
| **HWPX** | 자체 구현 (OOXML 유사 XML 직접 파싱) | `packages/core` | **v0.1.0** |
| **PDF** | 자체 구현 (pdfplumber + pypdf 비트맵) — 표 인식 32개 vs markitdown 0개 | `packages/core` | **v0.2.0** (비트맵) |
| **DOCX** | 자체 구현 (python-docx) — 속도 50배 우위 | `packages/core` | **v0.1.0** |
| **PPTX** | markitdown 위임 (text 23K vs 자체 170) | `packages/core` | v0.3 |
| ~~DOC~~ | **영구 미지원** — 사용자가 신버전 .docx 로 변환 후 업로드 | — | — |
| ~~PPT~~ | **영구 미지원** — 사용자가 신버전 .pptx 로 변환 후 업로드 | — | — |

DOC/PPT 는 LibreOffice 의존성 (200MB+ system binary) 회피 결정으로 영구
미지원입니다. 자세한 근거 및 우회 방법은
[`worklog/009_no_libreoffice_decision.md`](worklog/009_no_libreoffice_decision.md).

자세한 의사결정 근거:
- Phase 0: [`worklog/001_phase0_benchmark_decision.md`](worklog/001_phase0_benchmark_decision.md)
- v0.2 의존성 매트릭스: [`worklog/006_v0.2_dependency_matrix.md`](worklog/006_v0.2_dependency_matrix.md)
- LibreOffice 영구 금지: [`worklog/009_no_libreoffice_decision.md`](worklog/009_no_libreoffice_decision.md)

---

## 설치 (사내 사용)

사내 PyPI 미운영 → git 직접 설치.

```bash
# 코어만 (PDF / DOCX / HWPX)
pip install "git+https://github.com/Brad0329/korean-doc-parser.git#subdirectory=packages/core"

# HWP 포함 (+ AGPL extras)
pip install "git+https://github.com/Brad0329/korean-doc-parser.git#subdirectory=packages/core"
pip install "git+https://github.com/Brad0329/korean-doc-parser.git#subdirectory=packages/hwp"

# 풀세트 (AI 라벨링까지, v0.4+ 예정)
pip install "git+https://github.com/Brad0329/korean-doc-parser.git#subdirectory=packages/pipeline"
```

---

## 사용 예시 (v0.2.0)

```python
import korean_doc_parser_hwp  # noqa  ─ .hwp 라우팅 활성화 (옵트인)
from korean_doc_parser import extract

# PDF / DOCX / HWP / HWPX 모두 동일한 ParseResult 반환
result = extract("입찰공고.hwp")

print(result.markdown)          # 마크다운 본문
print(result.metadata.format)   # "hwp"
print(len(result.tables))       # 표 개수

for tbl in result.tables:
    print(tbl.rows)             # list[list[str]] — 사용자가 원하는 형식으로 직렬화

# PDF 이미지는 v0.2.0 부터 실 비트맵 + sha256 (v0.1.x 의 placeholder 제거)
result = extract("제안서.pdf")
for img in result.images:
    print(img.sha256, img.width, img.height, img.file_path)
```

지원 확장자 확인:

```python
import korean_doc_parser_hwp  # noqa
from korean_doc_parser import supported_extensions
print(supported_extensions())   # ('.docx', '.hwp', '.hwpx', '.pdf')
```

검수 파이프라인 (`korean-doc-parser-pipeline`) 은 v0.4+ 마일스톤에서 본격 구현됩니다.

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
- **HWP extras** (`packages/hwp`): **AGPL-3.0-or-later** — [`packages/hwp/LICENSE`](packages/hwp/LICENSE)

HWP 패키지가 pyhwp (AGPLv3+) 의존성 때문에 AGPL 격리되어 있습니다.
HWP 를 쓰지 않으면 코어 MIT 만으로 충분합니다.

> **참고:** v0.1.0 시점에 packages/hwp 를 GPL-3.0-or-later 로 표기했었으나
> pyhwp 실 라이선스가 AGPLv3+ 임을 v0.2.0 출시 시 정정함. 격리 전략(extras-only)
> 은 동일하게 작동.

---

## 슬로건

> **"HWP-aware document-to-markdown library for Korean documents.**
> A markitdown alternative with native HWP/HWPX support."
