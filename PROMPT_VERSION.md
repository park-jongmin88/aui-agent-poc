# 프롬프트 버전 처리 정리

> prompt 에셋을 '별칭 의존' 에서 '버전 번호' 방식으로 바꾼 기록.
> 관련 커밋: prompt.py 버전 로드 전환 (a646523)

---

## 1. 무엇이 문제였나

- 다른 프롬프트(예: PROMPT_EXPERT)를 골라도 항상 default
  ("당신은 친절한 Agent입니다")가 들어갔다.
- trace 를 보면:
  ```
  ctx { prompt_id: "PROMPT_EXPERT" }      ← 선택은 정상 전달됨
  resource { default: "...", alias: "production", cache: {} }  ← default 가 쓰임
  ```
- 원인: prompt.py 가 `prompts:/{id}@production` (별칭) 으로 로드하는데,
  PROMPT_EXPERT 에는 **production 별칭이 안 달려 있어서** 로드 실패 → default 폴백.

---

## 2. 별칭 vs 버전 (개념)

- MLflow 프롬프트는 이름별로 **버전이 쌓인다**.
  ```
  PROMPT_EXPERT
    ├─ v1
    ├─ v2   ← @production (별칭이 가리키는 버전)
    └─ v3
  ```
- **별칭(alias)** = 한 프롬프트의 여러 버전 중 어느 걸 쓸지 가리키는 포인터.
  - 운영/스테이징 구분처럼 "버전을 코드에서 분리" 하려는 용도.
  - 단점: 프롬프트마다 별칭을 일일이 달아줘야 함 (안 달면 로드 실패).
- **우리 경우**: 여러 프롬프트를 이름으로 골라 쓰는 상황이라
  별칭보다 **버전 번호** 가 직관적. (운영/스테이징 구분이 목적이 아님)

---

## 3. 최종 방향 (확정)

**UI 를 "프롬프트 선택 → 버전 선택" 2단계로** 가고,
prompt.py 는 **버전 번호로 직접 로드** (별칭 의존 제거).

### 동작 흐름
```
1. 프롬프트 목록 조회
   ├─ 목록 없음   → default 프롬프트 사용
   └─ 목록 있음   → 이름 + 버전 개수 표시
         PROMPT_A [3]   ← 버전 3개
         PROMPT_B [1]
              ↓ (PROMPT_A 선택)
2. 버전 목록 조회
         v1 / v2 / v3
              ↓ (v2 선택)
3. 확정: prompts:/PROMPT_A/2 로딩  (이름 + 버전번호)
```

---

## 4. prompt.py 가 하는 일 (반영됨)

| 함수 | 역할 |
|------|------|
| `build(conn)` | 폴백(default) + 캐시 준비. (별칭 필드 제거됨) |
| `list_prompts()` | UI 1단계용. `[{name, versions}]` 반환 → `PROMPT_A [3]` |
| `list_versions(name)` | UI 2단계용. 그 프롬프트의 버전 번호 목록 `[1,2,3]` |
| `_latest_version(name)` | 버전 미지정 시 최신(최대) 버전 번호 |
| `_load_system(pid, version, resource)` | `prompts:/{id}/{version}` 로 로드, 캐시. version 없으면 최신 |
| `run(ctx, resource)` | ctx 의 prompt_id(+prompt_version)로 채움. 실패/미선택 → default |

### 계약 변화 (client → 서버)
- 기존: `ctx["prompt_id"]` 만
- 변경: `ctx["prompt_id"]` + (선택) `ctx["prompt_version"]`
  - prompt_version 없으면 **최신 버전** 자동 로드.

### 로드 URI
- 기존: `prompts:/{id}@{alias}`  (별칭 의존)
- 변경: `prompts:/{id}/{version}`  (버전 번호)
  - 완전한 `prompts:/...` URI 를 직접 보내면 그대로 사용.

### 폴백 (안전망)
```
프롬프트 목록 없음            → default
prompt_id 미선택             → default
선택했는데 로드 실패          → default
정상                        → 해당 버전 로드
```

---

## 5. 캐시 키 주의

- 캐시 키가 기존 `prompt_id` 에서 **`"id@version"`** 으로 바뀌었다.
  (같은 프롬프트라도 버전이 다르면 다른 캐시 엔트리)
- 같은 (id, version) 반복 호출은 서버 왕복 없이 캐시 사용.

---

## 6. 버전 조회 API (OSS 주의 — 중요)

### 핵심: search_prompt_versions 는 Databricks 전용
- `MlflowClient().search_prompt_versions(name)` 는 **Databricks 백엔드에서만** 동작한다.
- 우리처럼 **자체 호스팅(OSS) MLflow** 에서는 이 API 가 없어서 versions 가 항상 0 으로 나온다.
- MLflow 버전(3.10 / 3.13) 차이가 아니라, **OSS vs Databricks** 차이다. (3.13 으로 올려도 동일)

### OSS 해법: load_prompt 로 순차 탐색
버전은 1,2,3... 으로 연속 증가하므로, v=1 부터 load 가 성공하는 만큼 센다.
```python
def list_versions(name, max_scan=100):
    nums, v = [], 1
    while v <= max_scan:
        try:
            mlflow.genai.load_prompt(name, version=v)  # 성공 = 그 버전 존재
            nums.append(v); v += 1
        except Exception:
            break          # 실패 = 더 이상 버전 없음 → 멈춤
    return nums
```
- 이 탐색은 **최초 선택 화면(목록 표시) 에서만** 호출된다.
  실제 대화 추론 경로에서는 호출되지 않으므로 약간의 비용은 문제없다.

### 프롬프트 로드 (별칭 없이 버전 번호로)
```python
mlflow.genai.load_prompt("name", version=3)   # 특정 버전
mlflow.genai.load_prompt("name")               # 버전 생략 → 최신
mlflow.genai.load_prompt("prompts:/name/3")    # URI 형식도 가능
mlflow.genai.load_prompt("prompts:/name@latest")  # @latest 별칭(예약어)도 가능
```

- UI 2단계 화면(프롬프트→버전 선택)은 **포탈 UI 쪽 작업** (이 문서 범위 밖).
  prompt.py 는 그 선택값(prompt_id, prompt_version)을 받기만 하면 됨.

## 7. 현재 상태

- ✅ 별칭 의존 제거 → 버전 번호 로드로 전환
- ✅ list_prompts (버전 개수) / list_versions 추가 → 2단계 선택 지원
- ✅ 목록 없음 / 실패 시 default 폴백
- ⏳ search_prompt_versions API 정확성은 실환경 확인 필요
- ⏳ UI 2단계 화면은 포탈 쪽에서 구현
