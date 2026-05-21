# doc_parser 작업 규칙

> **프로젝트 형태 (2026-05-15 확정):** 사내 private 라이브러리. bidwatch 향후 사용 예정. 공개 OSS 가정 규칙(영문 docs/이슈 SLA/외부 라이선스 SLA) 은 모두 삭제됨.

## 새 세션 시작 시

1. **`HANDOVER.md` 정독** — 프로젝트의 모든 컨텍스트가 들어 있음. 이 파일 하나로 0에서 시작 가능
2. **현재 Phase 의 작업 로그 확인** — `worklog/` 의 최신 파일. 이전 세션의 결정/실패/잠재과제 이어받기
3. **현 phase 의 출구 게이트 (`HANDOVER.md` § 6)** 만족 여부 확인. 미달 시 그 Phase 마무리 우선

## Agent 역할 분담

- **메인 agent:** 코드 개발 + 설계 의사결정
- **테스트 agent (foreground):** 회귀 테스트 + 벤치마크 측정. PR 머지 전 또는 마일스톤 도달 시 실행. 통과 확인 후 다음 단계 진행

## 작업 로그 원칙

- **위치:** `worklog/` 디렉토리
- **파일 단위:** Phase 단위가 아니라 **마일스톤(v0.1, v0.2, ...) 또는 의사결정 단위**로 작성
- **작성 시점:** 마일스톤 도달 시 또는 큰 의사결정 시 메인 agent 가 직접 작성

### 코드에서 알 수 없는 것만 쓴다

1. **결정의 이유** — "A와 B 중 A 선택. 이유: ..." (코드는 What, 로그는 Why)
2. **외부 제약 조건** — 라이브러리 라이선스, API 키 절차, OS 차이 등 코드에 안 드러나는 것
3. **실패한 접근과 원인** — "X 시도 → 실패 → 원인 Y → Z 로 해결" (같은 실수 반복 방지)
4. **표면 근거 vs 진짜 근거** — 의사결정 시 둘을 분리해서 명시. 1차 작업의 PPTX 정책 흔들림 교훈

### 적지 않는 것

- 코드 구현 상세 (코드가 있다)
- git 히스토리 (git log 가 있다)
- 테스트 케이스 목록 (테스트 파일이 있다)
- 패키지 버전 (CHANGELOG.md 가 있다)

## 라이브러리 특화 규칙 (lets_portal 과 다른 점)

### 1. 공개 API 변경 시 SemVer 의무

`korean_doc_parser` 의 public API(`__init__.py` 노출 함수/클래스/타입) 변경 시:

- patch: 버그 수정만 (0.1.0 → 0.1.1)
- minor: 호환 가능한 추가 (0.1.0 → 0.2.0)
- major: 호환 깨짐 (0.x → 1.0)

PR 시 `CHANGELOG.md` 의 [Unreleased] 섹션에 항목 추가 필수. 안 적으면 머지 금지.

### 2. 단일 파일 포터빌리티 원칙 (코어 한정)

- `packages/core/src/korean_doc_parser/` 의 코드는 **외부 import 0건** 유지
- "외부" 정의: 표준 라이브러리 + 선택 의존성(pdfplumber 등 — 단, 옵션 import) 외 모두
- 다른 packages/\* 도 import 불가 (의존성 inversion — pipeline 이 core 를 import, 반대 안 됨)
- 위반 시 PR 자동 거절

### 3. 회귀 테스트 통과 의무

- 픽스처 25건 전수 통과 없이 main 브랜치 머지 금지
- pytest 커버리지 85% 미만이면 머지 금지
- mypy strict + ruff 통과 필수

### 4. ~~영문 docs 동시 갱신~~ ❌ 삭제 (2026-05-15 — 사내 private 결정)

- 한글 docs(`docs/ko/`) 만 유지. 영문 docs 의무 없음.
- 향후 공개 검토 시점에 영문 docs 추가 여부 재검토

### 5. 패키지 경계 침범 금지

```
packages/core/           ← 다른 어떤 패키지도 import 안 함 (가장 깨끗)
packages/hwp/            ← core 만 import 가능
packages/pipeline/       ← core 만 import 가능 (hwp 는 옵션 동적 import)
packages/segmenter/      ← core 만 import 가능
```

pipeline → hwp 직접 import 금지. hwp 가 필요하면 core 의 registry 를 통해 동적으로.

### 6. 벤치마크 회귀 ±5% 이내

- `benchmarks/compare.py` 실행 결과가 main 대비 처리 시간/메모리 ±5% 넘으면 PR 거절
- 회귀 정당화 가능: 라이센스 이슈/정확도 향상 등 명시적 이유 PR 본문에 적기

### 7. ~~이슈 응답 (공개 OSS 채택 시)~~ ❌ 삭제 (2026-05-15 — 사내 private 결정)

외부 SLA 없음. 단, 사내 정합성 유지:

- bidwatch 운영 중 발견된 파싱 실패 → 회귀 테스트로 영구 추가
- 의존성 보안 알림 분기 1회 점검
- Python 새 버전은 사내 운영 버전이 따라갈 때 호환

## 의사결정 규칙

### "표면 근거" vs "진짜 근거" 분리

1차 작업의 PPTX 정책 흔들림(2026-04-22 미지원 → 2026-05-14 자동 변환) 의 교훈:

- 결정 시 적은 근거가 "샘플 1/10 ROI" 였는데, 진짜 이유는 "다운스트림 segmenter 미스매치" 였음
- 표면 근거만 적으니 나중에 표면 근거가 약해지면 결정이 흔들림

**규칙: 의사결정 기록 시 두 항목 분리 작성**

- 표면 근거 (운영/시간/비용 등 측정 가능)
- 진짜 근거 (아키텍처/설계 의존성 등 본질)

### 단일 샘플 검증 금지

1차 작업의 D-1 발견 교훈:

- 파서가 경과원 ESG 1종 형식에만 동작 → 신규 제안서에서 섹션 0개로 "정상 완료"
- 원인: MVP 검증을 단일 샘플로 마감

**규칙:** 새 기능 합격 기준에 반드시 "샘플 N건 (N≥5) 통과" 명시. 단일 케이스 OK 로 다음 단계 진행 금지.

### 경쟁 라이브러리 검토 의무

1차 작업의 최대 실수:

- markitdown/marker/docling 등 글로벌 라이브러리를 검토하지 않음 → PDF/DOCX/PPTX 가 commodity 수준에 머묾

**규칙:** 새 포맷/기능 추가 시 반드시 최소 3개 경쟁 라이브러리 비교 후 결정. "직접 짤지 / 위임할지" 객관적 수치 근거 필요.

## 테스트 규칙

### 라이브러리는 Phase 가 아니라 마일스톤 단위

- 마일스톤(v0.1, v0.2, ...) 도달 시 테스트 agent 가 회귀 테스트 + 벤치마크 실행
- 통과 후 git tag + CHANGELOG 갱신 + 다음 마일스톤 진입

### 픽스처 3중 출처

저작권 안전한 테스트 데이터:

1. **자체 합성** (30건) — LaTeX→PDF, python-docx→DOCX, 한글 데모파일 등으로 생성
2. **공공 도메인** (20건) — data.go.kr, 정부 공고 (공공누리 1유형).
3. **익명화 추출** (옵션) — 실제 문서에서 회사명/금액 redact 후 구조만 보존. private repo 만

### Ground truth JSON

각 픽스처마다 동반:

```json
{
  "expected_sections": [...],
  "expected_table_count": N,
  "expected_image_count": N,
  "expected_text_length_range": [min, max],
  "expected_keywords": [...]
}
```

## 외부 OSS 참고 / 차용 정책 (2026-05-21 확정)

> 본 프로젝트는 사내 사용 + 좋은 외부 OSS 의 알고리즘/패턴 차용으로 품질 향상을 추구합니다. 외부 npm/PyPI 의존성 추가는 신중히, 코드 포팅은 자유롭게.

### 1. 호환 라이선스 (코어에 차용 OK)

- **MIT / Apache 2.0 / BSD / ISC / Unlicense** → `packages/core`, `packages/pipeline`, `packages/segmenter` 모두 차용 가능
- attribution 의무만 준수 (아래 §3)

### 2. 비호환 라이선스 (격리 필수)

- **GPL v3 / AGPL / SSPL** → `packages/hwp/` 안에서만 사용 가능 (이미 GPL 격리됨)
- 코어/파이프라인/세그멘터에 차용 금지 — viral 영향
- 의심 시 `LICENSE` 파일 확인 + `licensecheck` / `pip-licenses` 도구로 자동 점검

### 3. 차용 시 의무 절차

1. 차용 대상의 **commit 해시 + 파일 경로 + 라인 범위** 기록
2. 포팅한 우리 코드의 함수/모듈 docstring 에 출처 명시:
   ```python
   """알고리즘 X.

   Adapted from <project> (<license>, <url>), commit <hash>,
   file <path>. Re-implemented in Python.
   """
   ```
3. **`NOTICE.md`** (repo 루트) 에 누적 등록 (단일 진실원)
4. **`CHANGELOG.md`** 의 해당 버전에 차용 사실 명시
5. **`worklog/`** 에 차용 결정 기록 (이유 + 보완하는 우리 한계)

### 4. 추가 점검

- 알고리즘에 특허/분쟁 이슈 없는지 사전 확인 (공지 사양은 OK)
- 픽스처 N≥5 통과 + 회귀 ±5% 이내 (CLAUDE.md §"라이브러리 특화 규칙 §6")

자세한 정책 적용 예시는 `worklog/004_kordoc_review.md` 참고.

---

## 보안 / 운영 규칙

### 의존성 추가 시

- pyproject.toml 의 `dependencies` 에 추가 전 라이선스 확인 의무
- GPL/AGPL/SSPL 의존성은 hwp 패키지로만 격리
- 의존성 무게(`pip install` 후 `du -sh`) 가 50MB 초과 시 옵션 의존성으로 분리

### 시크릿 / 자격증명

- repo 에 절대 commit 금지 — `.env.example` 만 commit
- pipeline 패키지의 Claude API 키는 환경변수로만
- pre-commit hook 으로 secret scanner 권장 (`gitleaks` 등)

### CI (2026-05-15 — 사내 private 축소판)

- 모든 PR 은 CI 통과 필요 (GitHub Actions 또는 사내 러너)
- 매트릭스: **사내 운영 환경 한정** — Ubuntu LTS 1종 + Windows latest 1종 × Python 운영 버전 1종 (현 3.11)
- LibreOffice 설치 step 포함 (PPTX/PPT/DOC 변환 테스트용)
- 추후 공개 검토 시 매트릭스 확장

## Git 운영 규칙 (2026-05-20 확정)

### 1. Branch 전략
- **main 직접 commit** — 1인 개발이라 feature branch 불필요
- 향후 추가 인원 시 feature branch + PR 로 전환

### 2. Commit 메시지 — Conventional Commits
형식: `<type>(<scope>): <설명>`

**type:**
- `feat`: 새 기능 (public API 추가/확장 → minor bump)
- `fix`: 버그 수정 (→ patch bump)
- `refactor`: 기능 변경 없는 구조 개선
- `perf`: 성능 개선
- `test`: 테스트 추가/수정
- `docs`: 문서만 변경
- `chore`: 빌드/도구/의존성/잡일
- `ci`: CI 설정 (GitHub Actions 등)
- `build`: 빌드 시스템 / pyproject.toml

**scope (선택):** 패키지 이름 — `core`, `hwp`, `pipeline`, `segmenter`, `benchmarks`, `worklog`

**예시:**
- `feat(core): PDF 파서 구현 (pdfplumber 기반)`
- `fix(hwp): COM 폴백 시 인코딩 깨짐 해결`
- `test(core): HWPX 픽스처 5건 추가`
- `chore: ruff 0.5.0 의존성 업그레이드`

설명문은 한국어 OK (작업 로그도 한국어).

### 3. Push — commit 마다 즉시
- 매 commit 직후 `git push origin main`
- main **force push 절대 금지**
- **amend 금지** (push 후엔 새 commit 으로)

### 4. Commit 게이트 (Phase 1 부터)
매 commit 전에 통과해야 하는 조건. main 직접 commit 이므로 PR 머지 게이트와 동일.

| commit type | 필수 게이트 |
|---|---|
| `feat`, `fix`, `refactor`, `perf` | mypy strict + ruff + pytest 통과 |
| `feat` 중 public API 변경 | + `CHANGELOG.md [Unreleased]` 항목 추가 |
| `test`, `docs`, `chore`, `ci`, `build` | 게이트 면제 (단, 깨진 상태 push 금지) |

pre-commit hook 자동화 권장 (Phase 1 Day 1-2 구성).

---

## 한국어 / 영문 정책 (2026-05-15 — 사내 private 으로 완화)

- 코드 docstring: **영문 권장** (변수/함수명과 일관성 + 향후 공개 가능성 대비). 단 강제 아님 — 복잡한 한국 도메인 로직은 한글 OK
- 주석: 한글 또는 영문 자유
- 변수/함수명: 영문
- 작업 로그(`worklog/`): 한국어
- README: 한국어(`README.md`) 만 유지. 영문 README 의무 삭제
- 사용자 docs: `docs/ko/` 만 유지. 영문 docs 의무 삭제

향후 공개 검토 시점에 영문 docstring/README/docs 보강 검토.

## 코딩 스타일

- ruff 기본 + pyproject.toml 에 명시 (line length 100)
- mypy strict 통과
- 타입 힌트 의무 (특히 public API)
- f-string 권장, `.format()` 비권장
- Path 객체 권장 (str 경로 지양)

## 메모리 (저장된 메모리)

이전 lets_portal CLAUDE.md 에 있던 메모리 두 가지:

1. **한국어는 높임말** — 새 프로젝트에서도 유지. 메인 agent 응답은 ~합니다/~해요 체
2. **배포 방식 변경 — 서버+DB** — lets_portal 특화 항목. doc_parser 는 라이브러리라 무관. 제거.

새 프로젝트 메모리 (2026-05-15 확정):

- **사내 private 라이브러리** — 배포는 사내 PyPI 또는 git 직접 설치 (`pip install git+...`)
- **주 사용자 = bidwatch** (향후) + 사내 RAG/검색 프로젝트
- **5종 도메인** = 입찰공고 / 법률검토 / 공문 / 전람회 PDF / 제안서
- **7포맷** = HWP / HWPX / PDF / DOCX / DOC / PPTX / PPT
- **우선순위** = 정확도 > 속도 > 기능 다양성

## 첫 작업 시 (Phase 0) — 진행 상황

- [x] `HANDOVER.md` § 3 의 6가지 결정 사항 답 작성 (2026-05-15)
- [x] `worklog/000_handover_received.md` 작성
- [ ] Phase 0 벤치마크 스크립트 작성 (markitdown/marker/docling/unstructured vs 현 file_parser)
- [ ] 벤치마크 실행 + 결과 표 정리
- [ ] 포맷별 "위임 vs 자체" 결정 문서화
- [ ] Phase 0 출구 게이트 통과 → Phase 1 진입

## 한 줄 요약

> **사내 private 라이브러리.** 단일 파일 포터빌리티 + 패키지 경계 + SemVer + 회귀 테스트 의무. 영문 docs/외부 SLA 등 공개 OSS 의무는 삭제. 핵심 원칙(이유/제약/실패 만 기록)은 lets_portal 과 동일. `HANDOVER.md` 가 컨텍스트의 단일 진실원.
