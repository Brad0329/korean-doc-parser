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

### v0.5.0 시점 — **실 차용 0건**

v0.4.x ~ v0.5.0 동안 추가된 의존성 (anthropic SDK / python-pptx / markitdown /
pyhwp / pypdf 등) 은 모두 **pip 의존성** (License compatibility 표의 OK 범위)
으로 사용 — 알고리즘 / 코드 직접 차용 아님. caption regex 패턴 / 3중 가중
신뢰도 / Vision 호출 wrapper 등은 **자체 설계** (worklog/011 § B, worklog/019
§ 3).

### kordoc — 검토 완료, 미차용 보존 기록

- **Project**: [chrisryugj/kordoc](https://github.com/chrisryugj/kordoc)
- **License**: MIT
- **Adapted in**: _(미차용)_
- **Description**: v0.2 시점에 HWP 5.x CFB 파싱 / AES-128 ECB 암호화 HWP /
  손상 파일 복구 알고리즘이 후보로 검토됨. pyhwp 단독으로 합격 기준
  통과하여 실제 차용은 미진입. **차용 시 본 항목 활성화** + Adapted in /
  Commit / Worklog 채움.
- **Worklog**: [`archive/worklog/004_kordoc_review.md`](archive/worklog/004_kordoc_review.md)

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

| Upstream license | core (MIT) | hwp (AGPL-3.0-or-later) |
|---|---|---|
| MIT / Apache-2.0 / BSD / ISC / Unlicense | ✅ OK (attribution only) | ✅ OK |
| LGPL | ⚠️ Caution — usually OK for code adaptation, not for static linking; review per case | ✅ OK |
| **GPL-3.0** / AGPL / SSPL | ❌ **Forbidden in core (MIT) package** | ✅ OK (already AGPL-isolated via pyhwp) |

자세한 정책은 `CLAUDE.md` 참고.
