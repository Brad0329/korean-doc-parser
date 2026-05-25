# 000 — 인수인계 수신 및 Phase 0 결정 확정

**작성일:** 2026-05-15
**작성자:** 메인 agent
**유형:** 의사결정 (Phase 0 진입)

---

## 1. 받은 문서

- `HANDOVER.md` — lets_portal Phase D 진행 중 2026-05-14 작성. 프로젝트 컨텍스트 100%.
- `CLAUDE.md` — doc_parser 작업 규칙. lets_portal 모체 규칙 + 라이브러리 특화 7항목.

두 문서 정독 완료. `HANDOVER.md § 3` 이 요구한 5가지 결정 + § 7 명명 결정 + 추가 결정(DOC/PPT 포함) = **총 7개 결정** 확정.

---

## 2. 확정 결정 7개

| # | 항목 | 결정 |
|---|------|------|
| ① | 미래 프로젝트 시나리오 | 회사 내 생산 자료 **5종 도메인** — 입찰공고문(일부), 법률검토, 공문, 전람회 PDF, 제안서. 1차 호출자 = bidwatch (향후) |
| ② | 공개 / private | **사내 private.** 향후 공개 검토 보류 |
| ③ | 유지보수 SLA | **약속 없음** (사내 private 정합) |
| ④ | 라이선스 | **코어 MIT + HWP extras GPL v3 분리** (handover 추천 그대로) |
| ⑤ | segmenter 합류 | **합류.** 단, 현재 제안서 도메인 전용 → 4개 도메인 segmenter 후속 개발 필요 |
| ⑥ | repo 이름 | **`korean-doc-parser`** |
| 추가 | 지원 포맷 | 5포맷 → **7포맷** (DOC, PPT 추가 — LibreOffice 변환 경유) |

### 표면 근거 vs 진짜 근거 (CLAUDE.md 의사결정 규칙 적용)

#### ② private 결정
- **표면 근거:** 외부 contribution 받을 인력 여유 없음, 영문 docs 부담
- **진짜 근거:** bidwatch 1차 호출자가 사내 서비스라 외부 공개 가치가 작음. 코어 품질 안정화 전에 공개하면 평판 손실 위험. **유지보수 SLA 약속 없는 상태에서 공개 = 죽은 OSS = 손실** (handover § 3-3 의 "죽은 OSS 가 더 해롭다" 원칙)

#### ⑤ segmenter 합류 결정
- **표면 근거:** 이미 lets_portal D-2 에서 검증된 코드(매칭률 90.4%) 가 있어 재사용 효율적
- **진짜 근거:** doc_parser 만으로는 도메인 의미가 안 붙음. segmenter 가 없으면 호출자(bidwatch 등) 가 각자 의미 분류 코드를 짜야 함 → 코드 중복 + drift. **doc_parser → segmenter 파이프라인이 한 묶음일 때만 라이브러리 가치 있음.**

#### ⑤ 의 함의 — 위험 1건 명시
- 현재 segmenter 는 **제안서 도메인 전용**. 매칭률 90.4% 도 제안서 한정 수치.
- 다른 4개 도메인(입찰공고/법률검토/공문/전람회) segmenter 는 **아직 0건**.
- v0.1 출시 시 segmenter 동작 보장 도메인 = 제안서 1종. 나머지 4종은 v0.2~v0.5 후속 마일스톤.
- **착각 금지:** "segmenter 가져왔으니 5종 다 된다" 가 아님. 4종은 새로 짜야 함.

---

## 3. 결정에서 흘러나오는 작업 변경

### CLAUDE.md 가지치기 (완료)
- §4 영문 docs 동시 갱신 의무 → **삭제**
- §7 이슈 응답 SLA → **삭제**
- CI 매트릭스 → **사내 운영 환경 1종 한정**으로 축소
- "한국어/영문 정책" → 한글 README/docs 만 유지로 완화
- 메모리 항목 갱신: 7포맷/5도메인/bidwatch 1차 호출자

### handover.md 결정 박기 (완료)
- §3-1 ~ §3-5: 각 ❓ 에 결정 답변 박음
- §7: 명명 확정 박음
- §1-3, §2-2, §2-6, §6: DOC/PPT 추가 반영 (이전 작업)

---

## 4. 다음 할 일 (Phase 0 후반)

CLAUDE.md "첫 작업 시 (Phase 0)" 의 진행 상황대로:

- [x] 6가지 결정 답변 작성
- [x] worklog/000 작성
- [ ] **Phase 0 벤치마크 스크립트** 작성 (`benchmarks/compare.py`)
  - 대상: markitdown / marker / docling / unstructured / 현 lets_portal file_parser
  - 측정: 텍스트 완성도, 표 보존율, 처리 시간, 메모리, 의존성 무게
  - 샘플: 25건 (자체 합성 + 공공도메인 — 회사 자산 절대 금지)
- [ ] 벤치마크 실행 + 결과 표 정리 (`docs/benchmarks/phase0_result.md`)
- [ ] 포맷별 위임 vs 자체 결정 문서화 (`worklog/001_phase0_benchmark_decision.md`)
- [ ] Phase 0 출구 게이트 확인 → Phase 1 진입

### 벤치마크 결과로 결정할 5개 포맷 (HWP/HWPX 는 자체 구현 확정)

| 포맷 | 위임 후보 | 자체 구현 후보 |
|------|----------|---------------|
| PDF | markitdown / marker / docling | pdfplumber + 자체 |
| DOCX | markitdown / docling | python-docx + 자체 |
| DOC | LibreOffice → DOCX 위임 경로만 | (없음) |
| PPTX | markitdown / docling | 현 LibreOffice 변환 + 자체 |
| PPT | LibreOffice → PPTX 위임 경로만 | (없음) |

DOC/PPT 는 LibreOffice 변환 경유라 위에서 결정되는 DOCX/PPTX 파서를 그대로 따라감.

---

## 5. 위험 / 잠재 과제 (다음 세션이 이어받을 것)

1. **샘플 데이터 부족** — handover § 5-2 의 (주)렛츠 제안서 10건은 회사 자산이라 그대로 못 씀. 합성/공공도메인 25건을 Phase 0 안에 확보해야 벤치마크 가능. **이 작업이 의외로 시간 큰 항목.**
2. **segmenter 4종 도메인 개발 미정** — v0.1 출시 시 segmenter = 제안서 1종 한정임을 README/CHANGELOG 에 명시 필요. bidwatch 측에 "다른 도메인은 아직" 사전 공지 필요.
3. **HWP/HWPX 차별화 점검 방법 미확립** — 글로벌 라이브러리들이 HWP 지원 시작했는지 Phase 0 벤치마크에서 확인. 만약 markitdown 이 최근에 HWP 지원 추가했으면 차별화 영역이 사라질 수 있음.
4. **LibreOffice 의존성 무게** — 7포맷 중 PPTX/PPT/DOC 3개가 LibreOffice 변환 경유. CI 에서 LibreOffice 설치 시간/안정성 우려. 옵션 의존성으로 격리 필요할 수 있음.

---

## 6. 한 줄 요약

> 6+1 결정 확정 → handover/CLAUDE 가지치기 완료 → 다음은 Phase 0 벤치마크. 벤치마크 결과로 5포맷(PDF/DOCX/DOC/PPTX/PPT) 위임 vs 자체를 객관 수치로 결정한 뒤 Phase 1(코드) 진입.
