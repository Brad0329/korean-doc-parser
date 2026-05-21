# 003 — HWP 의 서버 정합성 확인 (1차 file_parser.py 회독)

**작성일:** 2026-05-21
**작성자:** 메인 agent
**유형:** 의사결정 (다음 세션이 같은 의문을 또 겪지 않도록 메모)

---

## 1. 무엇이 의문이었나

v0.2 의 HWP 처리를 고민하면서 "한/글 COM 폴백이 Windows + 한/글 정품에 의존하는데,
bidwatch 같은 **서버 환경에서는 어떻게 돌리나?**" 가 큰 의문이었음.

이 의문이 다음 세션에서 또 떠오를 수 있어서 결론을 영구 기록.

---

## 2. 1차 작업 코드 확인 — `lets_portal/backend/utils/file_parser.py`

`_parse_hwp` 의 실제 구조:

```python
def _parse_hwp(path, raw):
    # 1차: pyhwp (Pure Python, 모든 OS, 한/글 불필요)
    result = _parse_hwp_pyhwp(path, raw)
    if result.error is None:
        return result            # ← 대부분 여기서 끝
    # 2차: COM 폴백
    com_result = _parse_hwp_com(path, raw)
    ...
```

`_parse_hwp_com` 의 첫 줄:

```python
def _parse_hwp_com(path, raw):
    if platform.system() != "Windows":
        return ParseResult(error="COM 폴백은 Windows + 한/글 설치 환경에서만 동작", ...)
    ...
```

→ **Linux 서버에서는 COM 자동 skip.** pyhwp 단독으로 처리.

코드 docstring 명시:
- 1차 pyhwp: **"한/글 프로그램 불필요, 모든 OS에서 동작, 표 내용까지 추출"**
- 2차 COM: **"한/글 설치 환경에서만 동작, 품질 최상"** (있으면 좋고 없어도 OK)

---

## 3. 결론

| 환경 | HWP 처리 |
|---|---|
| bidwatch (Linux Docker) | pyhwp 단독 ✅ |
| 개발자 Windows PC + 한/글 | pyhwp + COM 폴백 (품질 향상) ✅ |
| Linux/macOS 개발자 PC | pyhwp 단독 ✅ |

**한/글 COM 은 "필수" 가 아니라 "옵션적 품질 향상".** 모든 서버 환경에서 동작.

따라서 7포맷 전부 Linux Docker 서버에서 운영 가능:
- PDF / DOCX / HWPX / PPTX = Pure Python
- DOC / PPT = LibreOffice headless (apt-get 한 줄)
- **HWP = pyhwp 단독** (COM 은 개발자 PC 에서만 자동 활성)

---

## 4. v0.2 HWP 작업 가이드 (다음 세션용)

복잡한 워커 분리 / 사용자 사전 변환 / 한컴 API 같은 옵션 **모두 불필요**.

**그대로 이전:**
- `lets_portal/backend/utils/file_parser.py` 의 `_parse_hwp` (line ~407)
- `_parse_hwp_pyhwp` (line ~437) — pyhwp 의 `hwp5html` XSLT → XHTML → BeautifulSoup 마크다운
- `_parse_hwp_com` (line ~471) — pywin32 + 한/글 COM 자동화, platform.system() 가드
- `_xhtml_to_markdown` (line ~520) — XHTML → 마크다운 공용 변환기

**이전 위치:** `packages/hwp/src/korean_doc_parser_hwp/parser.py`

**의존성 (`packages/hwp/pyproject.toml`):**
```toml
dependencies = [
  "korean-doc-parser",
  "pyhwp",  # GPL v3 — 이 패키지가 GPL v3 격리된 이유
  "beautifulsoup4",  # _xhtml_to_markdown
  'pywin32 ; sys_platform == "win32"',  # 옵션 COM 폴백, Windows 만
]
```

**선결 작업:**
- pyhwp 3.11 호환성 검증 (pyhwp 가 3.6 까지 공식, 3.11 동작 여부 확인)
- 합성 HWP 픽스처는 불가능 (HWP 5.0 바이너리 spec 가 복잡) → 실제 sample 의존
  - `samples/*.hwp` 의 1건 (창업역량강화 제안서) 활용
  - `local` 마커로 CI 면제, 로컬 only 검증

---

## 5. 한 줄 요약

> **HWP 의 서버 정합성 문제는 없다.** pyhwp 단독으로 Linux 서버 OK, 한/글 COM 은 개발자 PC 의 옵션 폴백. 1차 작업 코드 그대로 이전이 답.
