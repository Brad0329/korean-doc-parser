# NOTICE — Third-party attributions

이 파일은 `korean-doc-parser` 가 외부 OSS 프로젝트의 **알고리즘 / 패턴 / 코드** 를
참고·차용한 항목의 attribution 을 누적 기록합니다.

차용 정책은 [`CLAUDE.md` §"외부 OSS 참고 / 차용 정책"](CLAUDE.md) 참고.

---

## 형식

각 항목은 다음 정보를 포함합니다:

- **Project**: 출처 프로젝트 이름 + 저장소 URL
- **License**: 출처의 라이선스
- **Adapted in**: 우리 repo 의 어느 파일/모듈
- **Commit / Version**: 차용 시점의 출처 commit 해시 또는 release 버전
- **Description**: 무엇을 차용했는지 (한 문장)
- **Worklog**: 의사결정 기록 위치

---

## Entries

### (참고만 — 아직 실제 코드 차용은 없음)

#### kordoc — 검토 완료, 차용 항목 식별됨 (v0.2+ 에서 실제 차용 시 본 항목 활성화)

- **Project**: [chrisryugj/kordoc](https://github.com/chrisryugj/kordoc)
- **License**: MIT
- **Adapted in**: _(미정 — 실제 차용 시 채움)_
- **Commit / Version**: _(차용 시점에 기록)_
- **Description**: HWP 5.x CFB 파싱 / AES-128 ECB 암호화 HWP 처리 / 손상 파일 복구 알고리즘 등 후보. 실제 포팅 시 항목별 분리 기록.
- **Worklog**: [`worklog/004_kordoc_review.md`](worklog/004_kordoc_review.md)

---

## 실제 차용 후 추가 예시 (템플릿)

```markdown
#### <Algorithm or feature name>

- **Project**: [<owner>/<repo>](<url>)
- **License**: <SPDX identifier — e.g. MIT, Apache-2.0>
- **Adapted in**: `packages/<pkg>/src/.../module.py` (function `foo()`, lines NN-MM)
- **Commit / Version**: `<short-hash>` (or `v<X.Y.Z>`)
- **Description**: <One sentence: what algorithm/pattern was adapted>.
- **Worklog**: [`worklog/<NNN>_<topic>.md`](worklog/<NNN>_<topic>.md)
```

---

## License compatibility quick reference

| Upstream license | core / pipeline / segmenter | hwp (GPL-3.0-or-later) |
|---|---|---|
| MIT / Apache-2.0 / BSD / ISC / Unlicense | ✅ OK (attribution only) | ✅ OK |
| LGPL | ⚠️ Caution — usually OK for code adaptation, not for static linking; review per case | ✅ OK |
| **GPL-3.0** / AGPL / SSPL | ❌ **Forbidden in MIT packages** | ✅ OK (already GPL-isolated) |

자세한 정책은 `CLAUDE.md` 참고.
