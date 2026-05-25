# vanasso.kr — PPTX / 일반 문서 업로드 처리 패턴

> **독자:** vanasso.kr 의 웹 백엔드 개발자
> **대상 라이브러리 버전:** `korean-doc-parser` v0.5.0+

vanasso.kr 의 admin / 사용자 업로드는 다양한 포맷 (특히 PPTX) 이 들어옵니다.
실 운영 케이스에서 발견되는 corrupt / 비표준 입력을 graceful 하게 처리하는
패턴을 정리합니다.

---

## 1. 설치 (최소 셋업)

```bash
# 코어만 (PDF / DOCX / HWPX / PPTX)
pip install "git+https://github.com/Brad0329/korean-doc-parser.git@v0.5.0#subdirectory=packages/core[pptx]"
```

- `[pptx]` extras = markitdown 80MB+ 의존성 포함 (onnxruntime / numpy / magika)
- HWP 가 필요하면 `packages/hwp` 추가 (AGPL 격리)
- Vision 라벨링이 필요 없으면 `[vision]` 생략 (Anthropic SDK 미포함)

---

## 2. 핵심 패턴 — 업로드 핸들러

```python
from pathlib import Path
from korean_doc_parser import extract, ParseError, supported_extensions


SUPPORTED_EXTS = supported_extensions()  # ('.docx', '.hwpx', '.pdf', '.pptx')
# HWP 도 처리하려면: import korean_doc_parser_hwp 후 위 set 재호출


def handle_upload(uploaded_file: Path) -> dict:
    """단일 업로드 → JSON 응답. 라이브러리 에러는 4xx 로 surface."""

    # 1) 확장자 화이트리스트 (라이브러리가 라우팅하지만 1차 게이트 권장)
    if uploaded_file.suffix.lower() not in SUPPORTED_EXTS:
        return {"error": f"unsupported format: {uploaded_file.suffix}"}, 400

    # 2) 파싱 — ParseError 는 corrupt / 비표준 / 손상 케이스
    try:
        result = extract(uploaded_file)
    except ParseError as e:
        # samples/pptx_vanasso_upload1.pptx 같은 BadZipFile 케이스가 실제 발견됨
        return {"error": "document corrupt or unsupported variant", "detail": str(e)}, 422

    # 3) 응답 조립
    return {
        "format": result.metadata.format,
        "title": result.metadata.title,
        "markdown_preview": result.markdown[:2000],
        "table_count": len(result.tables),
        "image_count": len(result.images),
        "images": [
            {
                "sha256": img.sha256,
                "size": (img.width, img.height),
                "mime": img.mime_type,
                "page_no": img.page_no,  # PPTX 는 slide_no, HWP/DOCX 는 None
            }
            for img in result.images
        ],
    }
```

---

## 3. 실 운영에서 발견된 케이스

### 3-1. `pptx_vanasso_upload1.pptx` — BadZipFile

samples/ 에 박혀 있는 실 admin 업로드. 204-byte 손상 ZIP. 라이브러리가
`ParseError("Failed to parse PPTX ...: File is not a zip file")` 를 raise.

→ **`except ParseError` 로 잡아서 4xx (Unprocessable Entity) 응답**. 5xx 안
띄움.

### 3-2. PPTX 의 chart / smartart 만 있는 슬라이드

현재 `ExtractedImage` 는 `MSO_SHAPE_TYPE.PICTURE` 만 추출. chart / smartart
는 별도 XML 이라 비트맵 추출 불가. **markdown 본문에는 markitdown 위임으로
text 가 포함됨** — 차트 데이터를 텍스트로 가져갈 수는 있음.

→ vanasso 가 차트 이미지 자체를 필요로 하면 [`docs/internal/known-limitations.md`](../../internal/known-limitations.md)
§ B-1 참고 (v1.0+ 후보).

### 3-3. 큰 PPTX (142 슬라이드, 499 이미지)

`pptx_qvan_storyboard.pptx` 같은 큰 PPTX 는 `extract()` 가 약 2-3초 + 메모리
~100MB. **비동기 처리 권고** — Flask / FastAPI 의 background task 또는 별도
워커.

```python
# FastAPI 예시
from fastapi import BackgroundTasks

@app.post("/upload")
async def upload(file: UploadFile, bg: BackgroundTasks):
    saved_path = await save_temp(file)
    bg.add_task(handle_upload, saved_path)  # 응답 즉시 반환
    return {"queued": True}
```

### 3-4. tempfile 정리

`ExtractedImage.file_path` 는 라이브러리가 만든 OS tempfile. vanasso 가
이미지를 본인 storage (S3 / 로컬 파일시스템) 로 복사 후 사용 권고. 라이브러리
는 tempfile cleanup 책임 안 짐.

```python
import shutil

for img in result.images:
    if img.file_path:
        # 본인 storage 로 이동
        dest = vanasso_storage_dir / f"{img.sha256[:8]}_{img.width}x{img.height}.{img.mime_type.split('/')[-1]}"
        shutil.copy(img.file_path, dest)
```

---

## 4. Vision 라벨링 (옵션)

vanasso 가 업로드된 PPTX / PDF 의 이미지에 자동 caption / 분류를 원하면:

```python
from korean_doc_parser.vision import VisionClient
from korean_doc_parser.vision.cache import VisionCache

vision = VisionClient(cache=VisionCache("/var/cache/vanasso/kdp.db"))
# default = claude-haiku-4-5, 비용 0.6원/이미지

labels = []
for img in result.images:
    if img.width >= 100 and img.height >= 100:
        vr = vision.label(img.file_path)
        labels.append({
            "sha": vr.sha256,
            "caption": vr.caption,
            "type": vr.image_type,
            "confidence": vr.confidence,
            "cost_krw": vr.cost_krw,
        })
```

비용 정책 / `.env` 자동 로드 / hit_rate 확인은 README 참고.

---

## 5. 한 줄 요약

> vanasso.kr 는 `extract()` + `except ParseError` 만으로 시작 가능. corrupt
> 케이스는 4xx 로 surface, 큰 PPTX 는 비동기. tempfile 은 본인 storage 로
> 즉시 복사. Vision 은 옵션 (Haiku default 로 비용 1/10).
