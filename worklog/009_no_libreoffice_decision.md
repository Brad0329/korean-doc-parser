# 009 — LibreOffice 도입 금지 (영구 정책)

**작성일:** 2026-05-24
**작성자:** 메인 agent (사용자 결정)
**유형:** 영구 정책 결정 (architecture)
**선행:** `worklog/006` (v0.2 의존성 매트릭스) → `worklog/007` § 2-1 (v0.2 에서 LibreOffice v0.3 분리) → 본 결정 (v0.3 진입 직전 영구 폐기)

---

## 1. 결정 요약

**`korean-doc-parser` 의 어떤 패키지에도 LibreOffice 의존성을 추가하지 않는다.** 영구.

영향:
- HANDOVER 의 "7포맷 (PDF/DOCX/HWP/HWPX/DOC/PPTX/PPT)" 목표 → **5포맷 (PDF/DOCX/HWP/HWPX/PPTX)**
- v0.3 의 원래 계획 (DOC/PPTX/PPT 한꺼번에) → **PPTX 만** (markitdown 위임)
- `.doc` / `.ppt` 구버전 포맷은 **영구 미지원** (사용자가 직접 신버전으로 변환 후 업로드)
- 향후 같은 부담의 의존성(`soffice` CLI / `unoconv` / poppler-utils 등 system binary) 도 동일하게 금지

---

## 2. 표면 근거

- 두 도메인 신호 (2026-05-24 사용자):
  - **bidwatch**: HWP > HWPX > PDF > PPTX
  - **사내 RAG**: PDF > DOCX > PPTX
  - 양쪽 모두 **DOC / PPT 가 명단에 없음** → YAGNI
- PPTX 는 markitdown (Python 패키지) 로 처리 가능 — LibreOffice 불필요
- 이 두 사실만으로도 의사결정 자명

---

## 3. 진짜 근거 (도메인 신호와 무관하게도 유지될 이유)

### 3-1. web 서비스 컨텍스트의 비용 비대칭성

`korean-doc-parser` 의 호출자는 **서버 사이드** (bidwatch 백엔드 / 사내 RAG 서버) 가 거의 100%. end user 는 브라우저로 파일 업로드만 함. LibreOffice 도입 시 부담은 **운영자(= 우리) 가 매번** 짊어짐:

| 부담 | 빈도 | 추정 비용 |
|---|---|---|
| Docker 이미지 layer | 빌드 1회 (캐싱) | +200~300MB |
| CI 시간 | PR 마다 | +3-5분 |
| 런타임 메모리 | 변환 중 | +200-500MB RAM |
| 변환 wall time | 파일 1건 | +수 초 |
| 안정성 리스크 | 가끔 | hang / crash / 폰트 깨짐 |
| 보안 표면 | 정기 | CVE 모니터링 의무 |

end user 영향은 0 (잘 처리되면 그만) 이지만, 운영자(우리) 가 **6가지 부담을 매 PR / 매 컨테이너 / 매 변환에서 누적**.

### 3-2. boundary 종류 고정 (v0.2.0 결정의 연장)

v0.2.0 의 의사결정 (`worklog/006` § 4 진짜 근거) 는 **"의존성 boundary 를 Python 패키지 1종으로 통일"** 이었음. system 의존성(soffice CLI) 도입은 그 boundary 를 **두 종류** 로 깨는 행위. 한 번 깨면:
- 사용자 설치 절차 분기 (`pip install` + `apt install`)
- CI 매트릭스 분기
- 배포 환경 검증 분기 (LibreOffice 버전 호환성)

→ **boundary 1종 원칙은 v0.3 이후로도 유지** 가 본 결정의 진짜 의도.

### 3-3. 5포맷 = 사실상 100% 도메인 커버

도메인 신호에 따르면 DOC/PPT 합쳐 < 5%. 5포맷(PDF/DOCX/HWP/HWPX/PPTX) 이 도메인의 **>95% 를 커버**. 영구 미지원으로 잃는 가치 << 도입 시 매번 내는 비용.

### 3-4. "잘못된 길 다시 검토" 방지

`worklog/006` 시점에 LibreOffice 를 v0.3 으로 분리만 했고 폐기 결정은 안 했음. 다음 세션이 또 LibreOffice 채택을 검토하면 **같은 트레이드오프를 반복 분석** 하게 됨. 본 worklog 가 그 반복을 영구 차단. **결정 1회, 효력 무기한**.

---

## 4. DOC / PPT 가 진짜 필요한 사용자에게의 안내

영구 미지원이지만 우회 가능:

| 우회 방법 | 누가 한다 |
|---|---|
| 사용자가 한컴오피스 / MS Office 로 .doc → .docx 직접 변환 후 업로드 | end user |
| 서비스 운영자가 별도 변환 마이크로서비스 운영 (이건 `korean-doc-parser` 밖) | 운영자 |
| MS Graph API / Google Drive API 변환 서비스 호출 | 운영자 |

→ `korean-doc-parser` 의 책임 경계 밖. 우리는 **변환 후 결과** 만 받음.

---

## 5. 향후 같은 부담의 의존성 자동 금지

본 결정의 정합성을 유지하기 위해 다음도 같이 금지:

| 후보 | 왜 같은 부담인가 |
|---|---|
| `unoconv` | 내부적으로 soffice 호출 |
| `libreoffice-headless`, `soffice-bin` apt 패키지 | LibreOffice 별칭 |
| `pdf2image` (poppler-utils 의존) | system binary, 200MB+ poppler |
| `tesseract` (OCR) | system binary, 별도 언어팩 부담 |
| `wkhtmltopdf` | system binary, Qt 의존 |

→ 의존성 추가 시 **"Python 패키지 1종으로 처리 가능한가"** 가 항상 첫 질문.
"Python 패키지 1종" 불가능한 후보는 본 worklog 의 § 3-1 의 6가지 부담을 다시 평가 — 도메인 신호가 압도적이거나 (예: HWP) 운영 부담이 매우 작은 경우 (예: pypdf 2MB) 만 예외 채택.

---

## 6. v0.3 scope 재정의

기존 (worklog/006 § 1):
> v0.2 = HWP + PDF 비트맵. **LibreOffice 4포맷은 v0.3**.

본 결정 후:
> v0.3 = **PPTX 만, markitdown 위임**. DOC / PPT 는 **영구 미지원**.

작업량 추정 변경:
- 기존 v0.3: ~2주 (LibreOffice 의존성 매트릭스 + 3포맷 구현 + CI 설치 step)
- 새 v0.3: **~1-2일** (markitdown 어댑터 + PPTX 픽스처 + 테스트)

남은 마일스톤 로드맵도 가속:
- v0.3 → 1-2일
- v0.4 (Pipeline) → 1주
- v0.5 (검수 UI) → 1-1.5주
- v0.6+ (Active Learning) → 1주
- v0.7+ (Segmenter 5도메인) → ~5주

총 남은 작업: 이전 추정 ~10주 → **~9주** (LibreOffice 작업 1주 절약, scope 단순화로 v0.3 가속)

---

## 7. CLAUDE.md / HANDOVER / README / CHANGELOG 정정 항목

본 결정과 함께 같이 commit 되는 변경:

- `CLAUDE.md` — 새 섹션 "**금지 의존성**" 추가
- `HANDOVER.md` — § 1-3 (7포맷 → 5포맷), 상단 안내문에 영구 정책 링크
- `README.md` — 포맷별 처리 전략 표에서 DOC/PPT 행 제거 또는 "영구 미지원" 마킹
- `CHANGELOG.md [Unreleased]` — v0.3 scope 재정의

---

## 8. 한 줄 요약

> **LibreOffice 영구 금지. 7포맷 → 5포맷. v0.3 = PPTX (markitdown) 만, ~1-2일.**
> 진짜 근거는 **web 서비스의 운영자 비용 비대칭** + **boundary 1종 원칙** + **5포맷이 도메인 >95% 커버**. 도메인 신호가 바뀌어도 boundary 원칙으로 결정 유지.
