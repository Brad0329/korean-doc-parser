# 004 — kordoc 검토 + 차용 가이드

**작성일:** 2026-05-21
**작성자:** 메인 agent
**유형:** 외부 OSS 검토 + 향후 작업 참고

---

## 1. 검토 대상

- 저장소: [chrisryugj/kordoc](https://github.com/chrisryugj/kordoc)
- 언어: **JavaScript / TypeScript** (npm 패키지)
- 라이선스: **MIT** — 코드 차용 + 포팅 자유, attribution 의무
- 활성도: ★951 / Forks 182 / 122 commits / 최신 v2.7.2 (2026-05-16)
- 한 줄: "HWP, HWPX, PDF, XLSX, DOCX → Markdown. CLI + MCP Server"

---

## 2. 검토 이유 (사용자 의도)

> "상업화 안 함. 좋은 것 잘 copy/refer 해서 우리 것 upgrade."

→ kordoc 의 알고리즘/패턴을 Python 으로 포팅해 우리 라이브러리 품질 향상에 활용.
외부 npm 의존성 추가는 **하지 않음** (언어가 달라서 + 의존성 무게 회피).

---

## 3. 핵심 발견 — JS 라 직접 의존 불가, 코드 차용은 가능

| 차용 방식 | 가능 여부 | 비고 |
|---|---|---|
| npm 패키지 의존성으로 추가 | ❌ | 우리는 Python. Node 런타임 도입 부담 큼 |
| 알고리즘을 Python 으로 포팅 | ✅ | MIT-to-MIT, attribution 만 |
| 데이터 포맷 사양 학습 (HWP CFB 등) | ✅ | 코드 = 문서 |
| MCP 서버 인터페이스 패턴 참고 | ✅ | Phase 3 의 pipeline 패키지 |

---

## 4. 차용 우선순위

### 🔴 높음 — v0.2 또는 v0.3 에서 검토 권장

| # | 항목 | kordoc 위치 추정 | 우리 활용처 | 가치 |
|---|---|---|---|---|
| 1 | **HWP 5.x CFB 직접 파싱** | `src/` (cfb 라이브러리 사용) | `packages/hwp/` — pyhwp 가 깨지는 케이스 보완 | pyhwp 의 Python 3.11 호환성 / 일부 파일 깨짐 이슈 완화 |
| 2 | **AES-128 ECB 암호화 HWP** | 배포용 공문 처리 코드 | `packages/hwp/` — bidwatch 의 공공 문서 케이스 | 한국 관공서 배포 공문이 흔히 AES 적용 — 미지원이면 큰 공백 |
| 3 | **HWP 표 (병합 셀 / 중첩) 정확 추출** | 표 파싱 함수 | `packages/hwp/` + 향후 HWPX 개선 | pyhwp 의 표 처리 한계 보완 |

### 🟡 중간 — Phase 3 / v0.3+ 에서 참고

| # | 항목 | 우리 활용처 |
|---|---|---|
| 4 | **손상 파일 복구 (비표준 CFB)** | `packages/hwp/` — 실무에서 잦은 깨진 HWP 처리 |
| 5 | **MCP 서버 인터페이스 (8 tools)** | `packages/pipeline/` — Claude/Cursor 통합 시 설계 참고 |
| 6 | **한국어 패턴 감지 (어절 끊김, 구분/항목/종류)** | `packages/segmenter/` — 도메인 의미 청크 작업 시 휴리스틱 참고 |

### 🟢 낮음 — 현재 우리 도메인과 무관, 보류

| # | 항목 | 비고 |
|---|---|---|
| 7 | XLSX 지원 | HANDOVER §3-1 의 5종 도메인에 XLSX 거의 없음. 필요 시 markitdown 위임 |
| 8 | 문서 비교 (신구대조표) | 우리는 RAG 출력이 목표. 비교는 별개 |
| 9 | 마크다운 → HWPX 역변환 | RAG 출력 흐름이 단방향 (문서 → 마크다운) |

---

## 5. 차용 절차 (CLAUDE.md §"외부 OSS 참고 정책" 과 함께 적용)

### 5-1. 사전 점검
1. 차용 대상의 **라이선스 확인** (MIT/Apache/BSD = OK, GPL/AGPL/SSPL = 코어 금지)
2. 차용 시점의 **commit 해시 + 파일 경로 + 라인 범위** 기록
3. 해당 코드의 알고리즘 자체가 특허 등 분쟁 가능성 없는지 (공지 사양은 OK)

### 5-2. 포팅
1. JS 코드를 Python 으로 재구현 (직역이 아닌 의미적 포팅)
2. 함수/모듈 docstring 최상단에 출처 명시:
   ```python
   """HWP 5.x CFB walker.

   Algorithm adapted from kordoc (MIT, https://github.com/chrisryugj/kordoc),
   commit <hash>, file src/hwp/cfb.ts. Re-implemented in Python with type
   hints + strict mypy compliance.
   """
   ```
3. mypy strict + ruff + pytest 통과 (우리 게이트)

### 5-3. 라이선스 attribution
1. **`NOTICE.md`** (repo 루트) 에 항목 추가 — 누적 기록 단일 진실원
2. **`CHANGELOG.md`** 의 해당 버전 `Added` 또는 `Changed` 에 "kordoc 알고리즘 차용 (HWP 5.x CFB 파싱)" 식 명시
3. **`worklog/`** 에 차용 결정 기록 (어떤 commit 해시에서, 왜, 우리 어떤 한계 보완인지)

### 5-4. 회귀 검증
1. 픽스처 N≥5 통과
2. 우리 기존 동작 회귀 0건 (Phase 0 벤치마크 ±5%)

---

## 6. 즉시 활용 가이드 — v0.2 HWP 작업 시

`worklog/003` 의 결론: v0.2 HWP = pyhwp 단독 (Linux 서버 OK). 단, pyhwp 한계가 운영 중 드러나면:

1. **kordoc 의 `src/hwp/` 디렉토리 분석**
   - 파일별 책임 파악 (CFB 파싱 / 압축 해제 / 레코드 디코딩 / 텍스트 추출 / 표 처리)
   - 가장 가치 있는 1-2 모듈 식별
2. **Python 포팅 우선순위**
   - 사용자가 실제로 마주친 깨진 HWP 파일 케이스 우선
3. **위 §5 절차 따름**

---

## 7. 위협 (포지셔닝 측면, 비-기술적)

사용자가 상업화 의도 없으므로 위협이 약함. 단 기록 차원:

- kordoc 가 한국 OSS HWP 도구 시장 사실상 점유 (★951)
- 향후 공개 OSS 전환 (HANDOVER §3-2) 검토 시 차별점 명확화 필수:
  - **Python RAG 생태계** (kordoc 는 JS)
  - **AI 라벨링 + 검수 큐** (Phase 3 의 pipeline 패키지)
  - **5종 한국 도메인 의미 청크** (segmenter, kordoc 미보유)
- 단, 사내 private 동안엔 위협 0.

---

## 8. 한 줄 요약

> **kordoc = JS 라 의존 불가, 그러나 MIT 라 코드/알고리즘 포팅은 자유. v0.2 HWP 작업에서 pyhwp 한계 드러나면 kordoc 의 CFB 파싱 + AES 암호화 처리를 우선 차용. 절차는 §5 (출처 헤더 + NOTICE.md + worklog 기록).**
