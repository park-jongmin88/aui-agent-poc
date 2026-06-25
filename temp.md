# 최근 변경 내용 (작업 로그)

## 이번 세션 (gateway 인증 + 프롬프트 버전 + 보안)

### judge / gateway / evaluation 완성
- judge gateway 호출 인증 해결 — gateway 입구가 MLflow Basic 인증(아이디:비번)을 요구.
  litellm 1.89.3 이 LITELLM_EXTRA_HEADERS 환경변수를 안 읽어서, litellm.completion 을
  래핑해 매 호출에 Authorization: Basic 헤더를 강제 주입. (→ JUDGE_GATEWAY_AUTH.md)
- cost map 외부조회 경고 제거 — LITELLM_LOCAL_MODEL_COST_MAP=True (judge_eval.py 상단)
- judge 등록/평가 정상 동작 확인.

### 등록 단계별 한국어 진단 (agent.py)
- MLflow 연결정보 오류 시 영어 스택트레이스 대신 한국어로 원인 안내.
- 4단계(Tracking연결/Experiment/log_model/register_model)를 _step 으로 감싸
  실패 시 [항목 / 원본오류 / 확인사항 / 추정원인] 출력. 등록 시점만, 서빙 미변경.

### 프롬프트 버전 처리 (별칭 → 버전 번호)
- 문제: 다른 프롬프트 골라도 default 가 들어감 (production 별칭 없어서 로드 실패 → 폴백).
- 해결: 별칭 의존 제거, 버전 번호로 로드. "프롬프트 선택 → 버전 선택" 2단계.
- search_prompt_versions 는 Databricks 전용이라 OSS 는 load_prompt 순차탐색으로 버전 조회.
- 반영 파일: assets/prompt.py, assets/__init__.py(new_ctx prompt_version),
  aiu_custom/model_wrapper.py(list_versions mode), client.py(2단계 선택). (→ PROMPT_VERSION.md)

### trace 민감정보 마스킹 (보안)
- api_key 가 trace 에 남지 않도록 두 겹 방어:
  (1) _run 을 분리해 api_key 를 @mlflow.trace 함수 인자에서 제외(_run_traced).
  (2) span_processor 로 모든 span 의 api_key/password/token/secret 류를 [REDACTED] 마스킹.
- 반영: aiu_custom/model_wrapper.py. (재서빙 필요)

---

## 이전 세션 (요약)
- 셀프 judge 제거 → make_judge 정석 평가(judge_eval.py)로 전환, 5등급 자연어 평가.
- client surrogate 방어, 프롬프트 캐싱, 콜드스타트 워밍업.
- 구조 분리(config / aiu_custom / assets / agent), 진입점 aiu_custom.predict.ModelWrapper 표준화.

---

## 문서 안내
- README.md              — 프로젝트 개요 + 에셋 추가법
- AIU_AGENT_POC_SUMMARY.md — 아키텍처/설계결정 종합
- JUDGE_GATEWAY_AUTH.md   — judge gateway Basic 인증 트러블슈팅/동작원리
- PROMPT_VERSION.md       — 프롬프트 버전 처리(별칭→버전번호, OSS 순차탐색)
- TODO.md                 — 완료/할일 목록
