# 설계 기준 (DESIGN) — 개발 착수 전 확정본

무조건 발동하는 규칙과 강제 의존성을 **코드가 아니라 문서(.md)에서 제어**하기 위한 구조.
개발 전에 이 기준을 확정하고, 구현은 이 문서를 따른다.

---

## 1. 폴더 구조 (기준)

```
.opencode/
  AGENTS.md                    상위 규칙 진입점 — "무조건 발동 항목" 은 rules/ 를 가리킨다
  rules/
    always/                    ← 무조건 발동하는 규칙 (순서가 아니라 폴더로 관리)
      01-env-check.md          시작 시 .env 체크 규칙
      (이후 무조건 항목 추가)
  config/
    dependencies.md            ← 강제/추가 의존성 정의 (사람이 수정)
```

- **`rules/always/`** — "무조건 발동"하는 규칙들을 모으는 폴더. 순서 대신 폴더 소속으로 관리한다.
  새 항목이 생기면 여기에 `NN-<이름>.md` 로 추가한다.
- **`config/dependencies.md`** — requirements 에 강제로 들어갈 의존성을 사람이 직접 편집하는 파일.

---

## 2. rules/always/ — 무조건 발동 규칙

- 이 폴더 안의 규칙은 **7단계 흐름보다 먼저** 통과해야 하는 관문이다.
- AGENTS.md 는 "시작 시 rules/always/ 의 규칙을 모두 확인한다" 고 지시한다.
- 각 규칙은 md 파일 하나. 사람이 읽고 추가/수정할 수 있다.

### 첫 규칙: 01-env-check.md (시작 시 .env 체크)
- 루트 `.env` 에 MLflow 연결 정보가 있는지 확인한다.
  ```
  MLFLOW_TRACKING_URI=
  MLFLOW_TRACKING_USERNAME=
  MLFLOW_TRACKING_PASSWORD=
  ```
- `.env` 파일이 **없으면 생성**해주고, 값을 작성하라고 사용자에게 안내한다.
- 필수값(TRACKING_URI)이 비어 있으면 입력될 때까지 다음으로 진행하지 않는다.

---

## 3. config/dependencies.md — 강제 의존성 (사람이 수정)

requirements 생성 시 이 문서를 **기준으로 읽어** 반영한다. (코드 하드코딩 금지)

형식(안):
```markdown
## 필수 의존성 (무조건 포함)
- mlflow=={version}    # {version} 은 트래킹 URL 에서 조회한 버전으로 치환
- kserve==0.15.0

## 추가 의존성 (필요 시 한 줄씩)
- (예: pandas)
```

- `{version}` 은 트래킹 URL 조회 결과로 치환된다.
- 버전 조회 실패 시 기본값 `3.10.0` 을 사용하고, URL 재확인을 안내한다.
- 사람이 `kserve` 버전을 바꾸거나 의존성을 추가하려면 이 파일만 수정하면 된다.

---

## 4. MLflow 버전 조회 규칙

- 트래킹 URL 에 **표준 버전 조회 API** 를 호출해 MLflow 버전을 가져온다.
- 성공 → `dependencies.md` 의 `{version}` 치환에 사용.
- 실패 → URL 재확인 안내, 기본값 `3.10.0`.

---

## 5. requirements 반영 시점

- requirements 는 **파일 복사 후 내용 작성 단계**에서 채워진다.
- 생성 로직이 임의로 만들지 않고, **`config/dependencies.md` 를 읽어서** 반영한다.
- 즉 "무엇을 넣을지" 의 기준은 항상 md 파일에 있다.

---

## 6. 확정 사항 요약

| 항목 | 결정 |
|---|---|
| 무조건 발동 규칙 | 순서 아님 → `rules/always/` 폴더로 관리 |
| .env 없을 때 | 생성해주고 작성 안내, 필수값 없으면 진행 차단 |
| 강제 의존성 | `config/dependencies.md` 에서 사람이 제어 |
| mlflow 버전 | 트래킹 URL 표준 API 조회, 실패 시 3.10.0 |
| kserve | `==0.15.0` (dependencies.md 에 명시, 수정 가능) |
| requirements 반영 | 복사 후 작성 단계, dependencies.md 기준으로 읽어서 |

---

## 7. 미정 (나중에 확정)

- `rules/always/` 에 추가될 다른 무조건 항목들 (B — 추후)
- .env 필수 키의 최종 목록 (현재: TRACKING_URI/USERNAME/PASSWORD)
