# korean-doc-parser

> HWP / HWPX 를 포함한 한국어 문서를 마크다운 + 이미지 + 메타데이터 + Claude
> Vision 라벨로 변환하는 **사내 private 라이브러리**.

**현재 버전:** **v0.5.0** (2026-05-25). 5포맷 (PDF / DOCX / HWP / HWPX /
PPTX) 이미지 추출 + Vision CLI (`kdp-label`) + Pipeline 알고리즘 모듈
(`korean_doc_parser.pipeline`).

**DOC / PPT 영구 미지원** — LibreOffice 도입 영구 금지 (worklog/009).

---

## 5분 안 시작

```bash
# 1. 설치 (사내 PyPI 미운영 → git 직접)
pip install "git+https://github.com/Brad0329/korean-doc-parser.git@v0.5.0#subdirectory=packages/core"
pip install "git+https://github.com/Brad0329/korean-doc-parser.git@v0.5.0#subdirectory=packages/hwp"  # HWP 처리 시 추가
```

```python
# 2. 파싱
import korean_doc_parser_hwp  # HWP 자동 등록 (필요 시)
from korean_doc_parser import extract

result = extract("입찰공고.hwp")  # PDF / DOCX / HWPX / PPTX 모두 동일
print(result.markdown)              # 마크다운 본문
print(result.tables[0].rows)        # 표 → list[list[str]]
print(result.images[0].sha256, result.images[0].width)  # 이미지 메타
```

```bash
# 3. Vision 라벨링 (옵션, [vision] extras)
export ANTHROPIC_API_KEY=...        # 또는 .env 파일에 박음 (자동 로드)
kdp-label image.png                  # 단일 이미지
kdp-label --from-document doc.pdf    # 문서 전체 (5포맷 모두 동작)
kdp-label --stats                    # cache 누적 비용 / hit_rate
```

호출자별 자세한 패턴은 [`docs/ko/recipes/`](docs/ko/recipes) 참고:
- [`bidwatch.md`](docs/ko/recipes/bidwatch.md) — 입찰공고 파싱 + Vision + 자체 DB 저장
- [`vanasso.md`](docs/ko/recipes/vanasso.md) — PPTX 업로드 + corrupt 핸들링

---

## 포맷 지원 현황

| 포맷 | 텍스트 | 표 | 이미지 추출 | 비고 |
|---|---|---|---|---|
| **PDF** | ✅ pdfplumber | ✅ | ✅ pypdf 비트맵 (bbox=px) | v0.2.0 |
| **DOCX** | ✅ python-docx | ✅ | ✅ ZIP 내 media (bbox=none) | v0.1.0 |
| **HWPX** | ✅ XML 직접 파싱 | ✅ | ✅ ZIP 내 bindata (bbox=none) | v0.1.0 |
| **HWP** | ✅ pyhwp + bs4 | ✅ | ✅ pyhwp bindata (bbox=none) | v0.4.5 |
| **PPTX** | ✅ markitdown 위임 | (인라인) | ✅ python-pptx PICTURE shape (bbox=emu) | v0.4.4 |
| ~~DOC~~ | ❌ 영구 미지원 | — | — | 사용자가 .docx 로 변환 후 업로드 |
| ~~PPT~~ | ❌ 영구 미지원 | — | — | 사용자가 .pptx 로 변환 후 업로드 |

→ **`kdp-label --from-document` 가 5포맷 모두 동작.** 호출자는 본인 자체 DB
에 결과 저장 (라이브러리는 데이터 객체만 반환 — `docs/internal/known-limitations.md`
의 § 정책 참고).

---

## 패키지 구조

| 패키지 | 라이선스 | 설명 |
|---|---|---|
| `korean-doc-parser` | MIT | 메인 엔진 (PDF / DOCX / HWPX / PPTX) + Vision CLI + `pipeline` 알고리즘 모듈 |
| `korean-doc-parser-hwp` | AGPL-3.0-or-later | HWP 파서 (pyhwp 격리) |

```
korean-doc-parser/
├── packages/
│   ├── core/                   ← pip install korean-doc-parser
│   │   └── src/korean_doc_parser/
│   │       ├── core.py             # ParseResult / ExtractedImage / extract
│   │       ├── parsers/            # pdf / docx / hwpx / pptx
│   │       ├── vision/             # Claude Vision client + SQLite cache
│   │       ├── cli/                # kdp-label
│   │       └── pipeline/           # caption / confidence / doc_id (v0.5)
│   └── hwp/                    ← pip install korean-doc-parser-hwp
├── archive/                    ← historical (HANDOVER + 처리된 worklog)
├── docs/
│   ├── ko/recipes/             ← 호출자 사용 패턴
│   └── internal/               ← 메인테이너용 (known-limitations)
├── worklog/                    ← 현재 살아있는 결정 + 잠재 과제 출처
├── benchmarks/                 ← 벤치마크 비교 + baseline
└── scripts/                    ← eval_haiku 등 측정 자동화
```

---

## Pipeline 알고리즘 (v0.5+)

`korean_doc_parser.pipeline` 은 **stateless pure function 모음** — DB / 큐 /
UI 없음, 호출자가 자체 DB 책임 (worklog/019 의 결정).

```python
from korean_doc_parser.pipeline import (
    compute_doc_id,            # path → sha256 64-char hex (primary key 후보)
    weighted_confidence,       # regex 0.4 + proximity 0.2 + vision 0.4
    detect_caption_regex,      # 한국어 (<그림 N>) + 영문 (Figure N) 패턴
    detect_caption_proximity,  # bbox + text_blocks → 거리 기반 caption
)
```

호출자 사용 예시는 [`docs/ko/recipes/bidwatch.md`](docs/ko/recipes/bidwatch.md).

---

## Vision 모델 정책 (v0.5.0)

- **default = `claude-haiku-4-5`** — worklog/014 의 22건 실측에서 Sonnet
  대비 비용 1/10.6, 품질 동등 (93% 한국어 caption), 더 정직한 confidence
  calibration
- 정밀 필요 시: `--model claude-sonnet-4-5` 명시
- API 키: `.env` 의 `ANTHROPIC_API_KEY` 자동 로드 (Windows PowerShell 의
  empty env var quirk 까지 처리)

---

## 개발 환경 (메인테이너 용)

```bash
uv sync                              # 의존성 설치
uv run pre-commit install            # git hook 등록

uv run pytest                        # 232 test pass
uv run ruff check .                  # lint
uv run mypy packages/core/src packages/hwp/src packages/pipeline/src  # strict
```

코딩 규칙 / commit 게이트 / SemVer 의무 등은 [`CLAUDE.md`](CLAUDE.md),
v0.5.0 시점 살아있는 잠재 과제는 [`docs/internal/known-limitations.md`](docs/internal/known-limitations.md).

---

## 라이선스

- **코어** (`packages/core`): **MIT** — [`LICENSE`](LICENSE)
- **HWP extras** (`packages/hwp`): **AGPL-3.0-or-later** — pyhwp 의존성 격리
- 외부 OSS 차용 attribution: [`NOTICE.md`](NOTICE.md)

HWP 를 안 쓰면 코어 MIT 만으로 충분합니다.

---

## 슬로건

> **"HWP-aware document-to-markdown library for Korean documents."**
> A markitdown alternative with native HWP / HWPX bitmap extraction +
> Korean-tuned Claude Vision labelling.
