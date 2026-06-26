# Judge 평가 + AI Gateway 인증 정리 (트러블슈팅 + 동작 원리)

> judge_eval.py 로 평가가 안 되던 문제를 해결한 기록.
> 나중에 까먹으면 이 문서만 보면 됨. (litellm 버전·인증 방식이 핵심)

---

## 0. 한 줄 요약

**"gateway가 요구하는 Basic 인증(아이디:비번)을 litellm 이 안 실어주니까,
litellm.completion 함수를 가로채서(래핑) 매 호출에 Basic 헤더를 강제로 끼워넣었다."**

→ 이렇게 해서 gateway / judge / evaluation 전부 정상 동작하게 됨.

---

## 1. 전체 그림 (누가 누구를 부르나)

```
judge_eval.py (evaluate)
   ↓
make_judge(model="gateway:/hcp_latest")   ← gateway 모델 지정
   ↓
MLflow 가 "gateway:/" 를 보고 → 내부적으로 litellm 을 호출 엔진으로 사용
   ↓
litellm 이 gateway 엔드포인트로 HTTP 요청
   ↓
[gateway 입구 = MLflow Tracking Server] ← 여기가 HTTP Basic 인증을 요구!
   ↓ (인증 통과하면)
gateway → 실제 LLM(llm.com) 호출 → 평가 점수 반환
```

핵심 포인트 두 가지:
- **gateway 는 MLflow 서버 위에서 동작** → gateway 호출 인증 = MLflow 서버의 Basic 인증(아이디:비번)
- **gateway 모델을 쓰면 MLflow 가 litellm 을 통해 호출** → 그래서 에러가 litellm 에서 남
  (`pip install litellm` 이 gateway judge 의 의존성인 이유)

---

## 2. 무엇이 문제였나

### 증상
- judge 등록(register) 은 됨.
- 평가(evaluate) 시 trace 7건은 가져오는데, answer_quality 에 Error:
  ```
  litellm.AuthenticationError: OpenAIException - You are not authenticated
  ```
- gateway 로그에는 호출 기록이 없음 (= 호출 전에 차단됨).

### 원인 추적 (단계적으로 규명한 순서)
1. 무해한 경고들은 무시: spansLocation 기록 실패, FutureWarning(experiment_ids),
   litellm cost map 외부조회, Autolog(disable=True).
2. JUDGE_MODEL 은 `gateway:/hcp_latest` 로 정확히 지정됨 (접두사 OK).
3. gateway UI 의 "Try in Browser" 는 잘 됨.
   → 개발자도구(F12 > Network)로 그 요청 헤더를 보니:
   ```
   Authorization: Basic am9pMzJqcm9pZmk...   (MLflow 호스트/오리진)
   ```
   → base64 디코딩하니 "아이디:비번" 형태.
4. 결론: **gateway 입구는 MLflow 서버의 HTTP Basic 인증을 요구**한다.
   - `OPENAI_API_KEY`(Bearer 방식)로는 안 통함. Basic 과 방식이 다름.
   - judge_eval.py / Thunder Client(직접 POST) 둘 다 같은 에러
     → 코드 문제 아니고 **gateway 입구 인증** 문제로 확정.

### 왜 환경변수로는 안 됐나 (중요)
- 처음엔 `LITELLM_EXTRA_HEADERS` 환경변수에 Basic 헤더를 넣었지만 안 됨.
- 사용자 litellm 버전 = **1.89.3**.
- litellm 1.89.x 는 `LITELLM_EXTRA_HEADERS` 환경변수를 **SDK 직접 호출 경로에서 안 읽음**.
  (그 환경변수는 주로 litellm proxy 설정용)
- litellm 은 `completion(extra_headers=...)` 처럼 **함수 인자**로는 받음.
  하지만 make_judge 내부 호출이라 우리가 그 인자를 직접 못 넣음.

---

## 3. 해결 방법 — litellm.completion 래핑(가로채기)

litellm.completion 함수 자체를 우리 함수로 바꿔치기해서,
호출될 때마다 Basic 헤더를 강제로 끼워넣는다.

### 동작 순서
```
1. 아이디:비번 → base64 인코딩 → "Basic xxxxx" 헤더 문자열 생성
2. 원래 litellm.completion 을 보관(_orig_completion)
3. litellm.completion 을 새 함수(_completion)로 교체
4. _completion 은 호출 시 extra_headers={"Authorization":"Basic xxxxx"} 를
   강제로 병합한 뒤 _orig_completion 을 호출
5. (비동기 경로 litellm.acompletion 도 동일하게 패치)
6. 중복 패치 방지 플래그(_aiu_basic_auth_patched) 설정
```

### 핵심 코드 (judge_eval.py 의 _connect / _patch_litellm_basic_auth)
```python
def _connect():
    # 1) MLflow Tracking 서버 접속용 (trace 조회 등)
    os.environ["MLFLOW_TRACKING_USERNAME"] = MLFLOW_USERNAME
    os.environ["MLFLOW_TRACKING_PASSWORD"] = MLFLOW_PASSWORD
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

    # 2) gateway(litellm) 호출용 Basic 인증 헤더 주입
    import base64
    basic = base64.b64encode(f"{MLFLOW_USERNAME}:{MLFLOW_PASSWORD}".encode()).decode("ascii")
    _patch_litellm_basic_auth(f"Basic {basic}")
    os.environ.setdefault("OPENAI_API_KEY", "gateway-basic-auth")  # 빈 키 사전차단 방지용 더미


def _patch_litellm_basic_auth(auth_header: str):
    import litellm
    if getattr(litellm, "_aiu_basic_auth_patched", False):
        return

    def _merge_headers(kwargs):
        eh = dict(kwargs.get("extra_headers") or {})
        eh.setdefault("Authorization", auth_header)   # 이미 있으면 안 덮어씀
        kwargs["extra_headers"] = eh
        return kwargs

    _orig_completion = litellm.completion
    def _completion(*args, **kwargs):
        return _orig_completion(*args, **_merge_headers(kwargs))
    litellm.completion = _completion

    if hasattr(litellm, "acompletion"):
        _orig_acompletion = litellm.acompletion
        async def _acompletion(*args, **kwargs):
            return await _orig_acompletion(*args, **_merge_headers(kwargs))
        litellm.acompletion = _acompletion

    litellm._aiu_basic_auth_patched = True
```

---

## 4. 최종 동작 흐름 (성공 경로)

```
python judge_eval.py evaluate
   ↓
_connect()
   ├─ MLflow 인증 환경변수 설정 (trace 조회용)
   └─ _patch_litellm_basic_auth()  → litellm.completion 을 래핑(Basic 헤더 주입 버전)
   ↓
make_judge 가 평가 실행 → 내부에서 litellm.completion 호출
   ↓
래핑된 함수가 Authorization: Basic <아이디:비번> 헤더 실어서 gateway 호출
   ↓
gateway 입구(MLflow Basic 인증) 통과 → llm.com 모델 호출 → 점수 반환 ✅
```

성공 시 콘솔에:
`[정보] litellm 호출에 Basic 인증 헤더를 주입하도록 설정했습니다.`

---

## 5. 적용·재현 시 주의점 (나중에 까먹지 말 것)

1. **_connect() 가 gateway 호출 전에 불려야 함.**
   - 패치가 먼저 걸려야 하므로 register()/evaluate() 맨 앞에서 _connect() 호출. (현재 OK)
2. **아이디:비번이 정확해야 함.**
   - base64 디코딩값이 "Try in Browser" 의 Authorization: Basic 값과 같아야 함.
   - judge_eval.py 상단의 MLFLOW_USERNAME / MLFLOW_PASSWORD 에 채움.
3. **litellm 버전 의존(중요).**
   - 1.89.x 기준. litellm 메이저 버전이 바뀌면 completion 함수 구조가 달라져
     이 래핑이 안 먹을 수 있음 → 그때 재확인.
4. **gateway 입구 = MLflow Basic 인증** 이라는 게 핵심 전제.
   - gateway 설정/인증 방식이 바뀌면(예: Bearer 허용) 이 패치가 불필요해질 수 있음.
5. **왜 OPENAI_API_KEY 더미를 넣나** — litellm 이 빈 키면 호출 전에 막아버리는 경우가
   있어서, 사전 차단을 피하려 더미를 채움. 실제 인증은 Basic 헤더가 담당.

---

## 6. 같이 반영할 것 (아직 미반영 메모)

- **litellm cost map 외부조회 경고 끄기** (폐쇄망):
  ```python
  os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
  ```
  judge_eval.py 상단(import 전)에 추가하면 그 Warning 이 사라짐. (judge 동작과 무관, 경고만 제거)

---

## 7. 현재 상태

- ✅ gateway 호출 인증 해결 (Basic 헤더 주입)
- ✅ judge 등록 (register) 정상
- ✅ 평가 (evaluate) 정상 — trace 채점 → Feedback 점수 부착
- → **gateway / judge / evaluation 파이프라인 완성**

관련 커밋: judge_eval.py litellm 래핑 패치 (50cc5bf)
