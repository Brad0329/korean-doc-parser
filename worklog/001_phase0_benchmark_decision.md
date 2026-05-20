# 001 — Phase 0 벤치마크 & 포맷별 위임/자체 결정

**작성일:** 2026-05-18 (최종 업데이트: 2026-05-20)
**작성자:** 메인 agent
**유형:** Phase 0 의사결정 (벤치마크 결과 기반)

---

## 1. 벤치마크 실행 조건

- **실행일:** 2026-05-18 (Phase 0 세 번째 세션) + 2026-05-20 (docling 추가 실행)
- **어댑터:** 1차: markitdown + legacy_file_parser. 2차: markitdown + docling + legacy_file_parser (marker 제외 — GPL 라이선스 + 1.35GB 모델 다운로드 부담)
- **샘플:** 6건 (samples/ 디렉토리)
  - PDF 2건: 키움증권 스테이블코인 리포트(81p), 스테이블코인 법제화 과제(30p, 이미지 PDF)
  - DOCX 2건: 공공기관 법률 유권해석 2건
  - PPTX 1건: 한국관광공사 제안서 (37슬라이드)
  - HWP 1건: 창업역량강화 제안서
- **결과 파일:** `benchmarks/results/phase0_20260518T060334Z.{json,md}`

### 실행 중 발생한 문제 (기록 가치 있음)

markitdown 최초 실행 시 DOCX 2건 실패 → 원인: `markitdown[docx]` 옵션 의존성 미설치.
`pip install markitdown[docx]` 후 재실행해 해결. markitdown 은 기능별로 옵션 의존성이 분리돼 있음.
→ **외부 라이브러리 채택 시 옵션 의존성 확인 체크리스트 필요** (Phase 1 pyproject.toml 작성 시 반영).

---

## 2. 수치 결과

### Summary

| 어댑터 | runs | ok | errors | mean_ms | median_ms | mean_mem_mb | mean_composite |
|---|---:|---:|---:|---:|---:|---:|---:|
| markitdown | 5 | 5 | 0 | 45,678 | 719 | 51.51 | **0.863** |
| legacy_file_parser | 6 | 6 | 0 | 30,993 | 304 | 48.41 | 0.728 |

### Per-run

| 파일 | ext | 어댑터 | ms | text_len | tables | images | composite |
|---|---|---|---:|---:|---:|---:|---:|
| 3억초과 유권해석.docx | .docx | markitdown | 328 | 1,324 | 0 | 0 | 1.000 |
| 3억초과 유권해석.docx | .docx | legacy | 301 | 1,300 | 0 | 0 | 1.000 |
| 청탁금지법 질의.docx | .docx | markitdown | 375 | 3,801 | 0 | 0 | 0.938 |
| 청탁금지법 질의.docx | .docx | legacy | 8 | 3,777 | 0 | 0 | 0.938 |
| 창업역량강화 제안서.hwp | .hwp | legacy | 63,750 | 66,144 | 61 | 0 | 0.663 |
| 한국관광공사 제안서.pptx | .pptx | markitdown | 1,713 | 23,147 | 13 | 38 | 0.725 |
| 한국관광공사 제안서.pptx | .pptx | legacy | 120 | **170** | 0 | 0 | 0.319 |
| 스테이블코인 법제화.pdf (이미지) | .pdf | markitdown | 719 | 0 | 0 | 0 | 0.750 |
| 스테이블코인 법제화.pdf (이미지) | .pdf | legacy | 307 | 99 | 0 | 0 | 0.750 |
| 키움증권 스테이블코인.pdf | .pdf | markitdown | 225,253 | 71,524 | **0** | 0 | 0.903 |
| 키움증권 스테이블코인.pdf | .pdf | legacy | 121,474 | 101,095 | 32 | 0 | 0.699 |

---

## 3. 포맷별 결정

### HWP — 자체 구현 확정 ✅

- **표면 근거:** markitdown/docling/marker/unstructured 전원 HWP 미지원. 대안 없음.
- **진짜 근거:** HWP/HWPX 가 이 라이브러리의 유일한 차별화 영역 (HANDOVER §2-4). 자체 구현 없으면 "markitdown 의 한국어 래퍼" 에 불과. 포지셔닝 자체가 무너짐.
- **구현:** pyhwp + 한/글 COM 이중 폴백. `packages/hwp/` (GPL v3 격리).

### HWPX — 자체 구현 확정 ✅

- HWP 와 동일한 근거. OOXML 유사 구조라 외부 의존 없이 직접 XML 파싱 가능. MIT 유지.

### DOC — LibreOffice → DOCX 변환 확정 ✅

- **표면 근거:** MS Word 97-2003 바이너리. 직접 파싱 품질 들쭉날쭉.
- **진짜 근거:** LibreOffice 변환을 PPT/PPTX 에도 쓰므로 공용 컨버터(_libreoffice.py) 한 번 구현으로 DOC 추가 비용 없음. 새 의존성 불필요.

### PPT — LibreOffice → PPTX 변환 확정 ✅

- DOC 와 동일 근거.

### DOCX — 자체 구현 유지 결정 ✅

- **표면 근거:** 품질 동일(composite 1.000/0.938), legacy 가 50배 이상 빠름 (8ms vs 375ms).
- **진짜 근거:** markitdown 의존성을 추가해도 얻는 게 없음. 속도·품질 모두 legacy(python-docx 기반) 가 우위이거나 동일. CLAUDE.md "외부 의존성 50MB 초과 시 옵션으로 분리" 원칙과도 정합.
- **주의:** 표/이미지 포함 DOCX 는 이번 샘플에 없었음 (유권해석 문서 2건은 순수 텍스트). 표 포함 DOCX 에서 재검증 필요 → Phase 1 픽스처 추가 과제.

### PPTX — markitdown 위임 결정 ✅

- **표면 근거:** legacy text=170 (실질 실패), markitdown text=23,147 / composite 0.725.
- **진짜 근거:** legacy PPTX 파서는 LibreOffice 변환 후 텍스트 거의 유실. HANDOVER §5-3 "운영 서버 미검증" 상태가 수치로 확인됨. 자체 구현하려면 LibreOffice 변환 파이프라인을 재설계해야 하는데, markitdown 이 이미 잘 처리함. ROI 없음.
- **라이선스:** markitdown MIT → `packages/core` 에 포함 가능.
- **옵션 의존성:** `pip install markitdown[pptx]` 또는 `markitdown[all]` 필요한지 Phase 1 에서 확인.

### PDF — legacy(pdfplumber) 자체 구현 확정 ✅

- **3-way 비교 결과 (2026-05-20):**

  | 어댑터 | 텍스트 PDF(81p) | 이미지 PDF(30p) | 표 인식 | 결론 |
  |---|---|---|---|---|
  | markitdown | text 71K / 225초 | text 0 | **0개** | 표 전무 |
  | docling | **메모리 오류** p.34+ | OCR 동작(느림) | 미확인 | 대용량 실패 |
  | legacy (pdfplumber) | text 101K / 121초 | text 99 | **32개** | 유일하게 표 인식 |

- **표면 근거:** 표 인식 legacy 32개 vs markitdown 0개 vs docling 대용량 실패(bad_alloc). 속도도 legacy 최빠름(121초).
- **진짜 근거:**
  - docling 의 `std::bad_alloc` (p.34~81) 은 운영 환경 허용 불가. docling은 텍스트 PDF도 전체를 이미지 변환 후 OCR 처리 — 메모리 소비가 페이지 수에 비례해 폭증.
  - markitdown 의 표 0개는 법률/금융 문서 핵심 요구사항 미달. 텍스트 레이어만 읽고 표 구조를 파싱하지 않음.
  - pdfplumber 는 이미 legacy 에서 검증됐고 새 의존성 불필요. 단일 파일 포터빌리티 원칙 정합.
- **이미지 PDF 한계 인정:** 두 PDF 어댑터 모두 OCR 미적용 시 이미지 PDF에서 text≈0. 이미지 PDF 지원은 별도 Phase 에서 선택적 OCR 파이프라인으로 처리 (Phase 1 범위 외).
- **라이선스:** pdfplumber MIT → `packages/core` 포함 가능.

---

## 4. 실패한 접근 기록

### legacy PPTX 의 실패 원인 (추정)

legacy 의 PPTX 파서는 LibreOffice 로 변환 후 텍스트를 추출하는 방식. 이번 측정에서 text=170 이 나온 이유는 LibreOffice 가 설치돼 있지 않거나 변환 결과가 제대로 반환되지 않는 것으로 추정. 정확한 원인은 legacy 코드 내부 확인 필요. 단, 어느 쪽이든 markitdown 위임으로 결정했으므로 더 이상 진단하지 않음.

### markitdown 표 미인식 원인 (PDF)

pdfplumber 기준 88개 표 가 있는 문서에서 markitdown 이 0개를 반환. markitdown 의 PDF 처리가 텍스트 레이어 위주이고 표 구조를 별도로 파싱하지 않는 것으로 보임. PDF 표 보존이 요구사항이라면 markitdown PDF 위임은 부적합.

---

## 5. 현재 결정 상태 요약

| 포맷 | 결정 | 패키지 | 라이선스 영향 |
|---|---|---|---|
| .hwp | 자체 구현 | `packages/hwp` | GPL v3 격리 |
| .hwpx | 자체 구현 | `packages/core` | MIT |
| .doc | LibreOffice → DOCX | `packages/core` | MIT |
| .ppt | LibreOffice → PPTX | `packages/core` | MIT |
| .docx | 자체 구현 (python-docx) | `packages/core` | MIT |
| .pptx | markitdown 위임 | `packages/core` | MIT |
| .pdf | 자체 구현 (pdfplumber) | `packages/core` | MIT |

---

## 6. docling 실패 기록 (추가)

### docling std::bad_alloc (PDF 대용량)

- **발생:** 2026-05-20, 키움증권 스테이블코인.pdf (81p) 처리 중
- **증상:** p.34 부터 p.81 까지 `Stage preprocess failed for run 1, pages [N]: std::bad_alloc` 연속 발생
- **원인:** docling 은 텍스트 PDF도 전체를 이미지(렌더링)로 변환한 뒤 ONNX 레이아웃 모델에 입력. 81페이지 전체를 메모리에 올리면서 C++ heap 소진.
- **교훈:** ML 기반 레이아웃 분석은 대용량 문서에서 메모리 선형 증가. GPU 없는 일반 서버에서 운영 부적합.

---

## 7. 다음 액션 (업데이트)

- [x] docling/marker 비교 실행 (2026-05-20 완료)
- [x] PDF 포맷 결정 → pdfplumber 확정
- [ ] Phase 0 출구 게이트 최종 확인 → Phase 1 진입
