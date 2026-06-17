# skills - 스킬 목록

aiu-agent의 스킬 모음입니다. 각 스킬은 `SKILL.md`(에이전트용 설명)와 `scripts/`(실행 스크립트)로 구성됩니다.

> 스킬 이름은 **소문자 영숫자만** 허용됩니다 (deepagents 제약). 밑줄/하이픈/카멜케이스 불가.

---

## 작업 순서

```
init → validate → (localrun) → train → predict → (localserve) → deploy
                   * 선택                          * 선택
```

각 단계는 앞 단계를 통과해야 진행됩니다 (게이트). 상태는 `.aiu_state.json` 에 기록됩니다.

---

## 스킬 목록

| 순서 | 스킬 | 역할 | 게이트(필요 상태) | 스크립트 |
|---|---|---|---|---|
| 1 | **init** | source/ 분석 → run.py + model_wrapper.py 생성 | - | analyze_folder.py, generate_run.py |
| 2 | **validate** | run.py 9섹션 구조 / TODO 검증 | initialized | validate_run.py |
| 3 | **localrun** | MLflow 없이 로컬 학습 테스트 (선택) | validated | run_local.py |
| 4 | **train** | run.py 실행 → MLflow pyfunc 등록 | validated | run_train.py |
| 5 | **predict** | ① 로컬 추론 ② Endpoint 추론 | trained / endpoint_url | run_predict.py, inference_test.py |
| 6 | **localserve** | 로컬 FastAPI 서빙 (선택) | local_tested | start_server.py, stop_server.py |
| 7 | **deploy** | AI Studio Endpoint 배포 | predicted | deploy_run.py, deploy_client.py |

---

## 상태 흐름

```
initialized(0) → validated(1) → [local_tested(1.5)] → trained(2) → predicted(3) → deployed(4)
```

- `local_tested` 는 localrun 후 상태 (선택 단계)
- **localserve는 local_tested에서만** 동작 (results/ 의 로컬 모델 필요)
- train만 하면 MLflow에만 등록되어 로컬 파일이 없음

---

## 공통 모듈 (common/)

모든 스크립트가 사용하는 유틸리티입니다.

| 기능 | 함수 |
|---|---|
| 결과 출력 | `ok(data)`, `fail(message)`, `progress(message)` |
| 예외 안전 | `safe_main(entry_func)` — 진입점을 감싸 예외를 JSON으로 변환 |
| 게이트 | `check_gate(folder, skill)` |
| 파일 점검 | `check_files_consistency(folder)` — 삭제/수정 감지 |
| 재작업 | `rewind_to(folder, target_status)` — 상태 되돌림 |
| 상태 관리 | `get_state(folder)`, `set_state(folder, **kw)` |
| 현재 폴더 | `get_current_folder()`, `set_current_folder(name)` |
| 설정 | `get_mlflow_config()`, `get_aistudio_config()` |

---

## 스크립트 규약

모든 스크립트는 **JSON으로만** 결과를 출력합니다 (raw 트레이스백 노출 금지).

```json
{"status": "ok",       "data": {...}}      // 성공
{"status": "error",    "message": "..."}   // 실패
{"status": "progress", "line": "..."}      // 진행 중
```

- 진입점은 `safe_main()` 으로 감싸 어떤 예외도 JSON error로 변환합니다.
- 경로는 스크립트가 자동 계산합니다 (cwd 무관).

---

## 새 스킬 추가 방법

1. `skills/<이름>/` 폴더 생성 (이름은 소문자 영숫자만)
2. `SKILL.md` 작성 — `name`, `description`(트리거 포함)
3. `scripts/` 에 스크립트 작성 — JSON 반환, `safe_main` 적용
4. 게이트가 필요하면 `common/__init__.py` 의 `STAGE_REQUIRED` 에 추가
5. 이 목록(README.md)에 한 줄 추가
