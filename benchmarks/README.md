# benchmarks — Phase 0 비교 벤치마크

> Phase 0 출구 게이트의 두 항목 ("벤치마크 결과 표 생성", "어디는 위임 / 어디는 자체 결정 명문화") 을 수치로 뒷받침합니다.

## 1. 무엇을 비교하는가

| adapter | wraps | 라이선스 | 비고 |
|---|---|---|---|
| `markitdown` | Microsoft markitdown | MIT | OOXML 강함, HWP 미지원 |
| `marker` | VikParuchuri/marker-pdf | GPL-3.0 | PDF 전용, ML 기반 |
| `docling` | IBM docling | MIT | PDF/DOCX/PPTX, 구조화 강함 |
| `unstructured` | unstructured-io | Apache-2.0 | 카테고리 메타 풍부 |
| `legacy_file_parser` | lets_portal file_parser.py | — | 1차 작업 결과 — baseline |

doc_parser 자체 코드는 아직 없으므로 비교 대상이 아닙니다. Phase 1 v0.1 이후 어댑터 추가.

## 2. 무엇을 측정하는가

- **처리 시간** — `time.perf_counter` wall clock
- **메모리** — `tracemalloc` Python-allocated peak (RSS 아님 — 상대 비교용)
- **텍스트 완성도** — ground-truth 의 `expected_keywords` recall + `expected_text_length_range` in-range 여부
- **표 보존율** — `expected_table_count` 대비 정확도 (오차 허용치 `tolerance.table`)
- **이미지 보존율** — `expected_image_count` 대비 정확도
- **종합 점수 (`composite`)** — 위 4개 점수의 산술 평균. GT 가 부족하면 부분 평균.

의존성 무게는 별도 측정 — `pip install <pkg>` 후 `du -sh site-packages/<pkg>` 를 README 본문이 아닌 PR 본문에 첨부합니다.

## 3. 실행

```powershell
# 모든 포맷, 설치된 모든 adapter
python benchmarks/compare.py

# PDF 만, markitdown 과 docling 만
python benchmarks/compare.py --format pdf --adapters markitdown,docling

# legacy 경로 override
$env:LEGACY_FILE_PARSER = "C:\path\to\file_parser.py"
python benchmarks/compare.py --adapters legacy_file_parser
```

결과는 `benchmarks/results/phase0_<UTC-timestamp>.{json,md}` 로 저장됩니다.

## 4. 픽스처

`benchmarks/fixtures/README.md` 참조. 25건 수집은 Phase 0 후반의 가장 큰 작업 항목입니다.

## 5. Phase 0 출구 게이트와의 매핑

| 게이트 항목 | 이 디렉토리에서 해결되는 부분 |
|---|---|
| § 3 답 모두 작성됨 | 별도 — `worklog/000_handover_received.md` 참조 |
| 벤치마크 결과 표 생성됨 | `results/phase0_*.md` 의 `## Per-run results` 표 |
| "위임 vs 자체" 결정 명문화 | `worklog/001_phase0_benchmark_decision.md` 에 5포맷(PDF/DOCX/DOC/PPTX/PPT) 결정 작성 |

## 6. 한계 (정직하게)

- **메모리 = tracemalloc.** PyMuPDF/marker 같은 ML 라이브러리의 네이티브 heap 은 안 잡힙니다. 상대 비교용이며 절대값 해석 금지.
- **GT 작성자 bias.** 표/이미지 개수가 주관적인 문서가 있을 수 있음 — `tolerance` 로 완화.
- **단발 실행.** 첫 호출은 모델 로드로 느림. PR 회귀 측정에선 워밍업 후 N=3 반복 평균이 권장됩니다 (compare.py v0.2 후속).
- **OCR 비교 없음.** 스캔 PDF 의 OCR 품질 차이는 별도 트랙으로.
