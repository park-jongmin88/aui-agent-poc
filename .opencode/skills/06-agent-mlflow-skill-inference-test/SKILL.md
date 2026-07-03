---
name: agent-mlflow-skill-inference-test
description: Use only when the user explicitly asks "추론 테스트", selects step 6, "input_example.json", "inferencetest.py", or inference test after selected-model preparation is complete; posts input_example.json to the user-provided remote inference URL. Do not use for model number selection.
license: MIT
compatibility: opencode
metadata:
  flow: ml-workspace-development
  stage: 06-inference-test
  step: 6
---

# Inference Test

## Result First

```text
판단 결과: pass | warn | needs_user_input | blocked
현재 단계: 추론 테스트
진행 조건: 사용자가 6번을 선택했을 때만 실행
현재 대상: trained model project
핵심 판단: input_example.json, 원격 :predict req_url 입력 여부, HTTP request/response schema
다음 단계: 7. 오류 재실행
```

## Workflow

```text
1. 모델 목록 확인
2. 모델 선택
3. 환경 검증
4. 템플릿 변환
5. 원격 MLflow 등록 실행
6. 추론 테스트
7. 오류 재실행
```

## What To Do Now

```text
1. input_example.json을 확인한다.
2. inferencetest.py를 확인한다.
3. inferencetest.py의 req_url 값이 비어 있거나 :predict로 끝나지 않으면 사용자가 직접 입력하도록 안내한다.
4. inferencetest.py가 input_example.json을 읽고 원격 requests.post(req_url, headers, data)를 호출하는지 확인한다.
5. 응답 status_code와 JSON/text 출력이 가능한지 확인한다.
6. 로컬 모델 로드는 수행하지 않는다.
7. predict_2.py는 생성하지 않는다. 추론 테스트는 inferencetest.py를 사용한다.
8. 자동 실행하지 않는다. 사용자가 6번을 선택하거나 명시적으로 추론 테스트를 요청한 경우에만 실행한다.
```

## Output Contract

```text
반드시 보여줄 값:
- 판단 결과
- 사용한 input example
- 추론 entrypoint: inferencetest.py
- req_url 상태 (:predict URL 여부)
- predict 결과 요약
- response schema
- result_path: not written, unless --output is set
- 다음 단계
```

성공 출력 UI:

```text
판단 결과: pass
input_example: input_example.json
req_url: set
schema: JSON serializable
result_path: not written
next: 오류 재실행
```

## Commands

```text
실제 추론 실행:
python inferencetest.py

보조 스크립트:
python .opencode/scripts/06-inference-test/test_inference.py --project <선택모델작업폴더> --url http://server/v1/models/model:predict --execute
```

<details>
<summary>자세한 판단 기준 보기</summary>

```text
pass:
- input example 있음
- req_url 입력됨
- req_url이 원격 http:// 또는 https:// URL이고 :predict로 끝남
- HTTP 요청 성공
- output schema 확인됨

warn:
- HTTP 응답은 왔지만 JSON 파싱은 실패해 text로 출력함
- 결과가 길어 요약 출력함

needs_user_input:
- input example이 없음
- 어떤 추론 entrypoint를 사용할지 모호함

blocked:
- req_url이 비어 있음
- req_url이 :predict 경로가 아님
- HTTP 요청 실패
- 응답을 직렬화할 수 없음
```

</details>

<details>
<summary>문제 해결 보기</summary>

```text
증상: req_url 값을 입력하라는 메시지가 나옴
원인: inferencetest.py의 req_url이 빈 문자열
조치: 배포된 원격 추론 URL을 req_url에 직접 입력한 뒤 다시 실행. URL은 :predict로 끝나야 함

증상: input_example 없음
원인: 테스트 입력 누락
조치: input_example.json 또는 README 예제를 먼저 확정

증상: predict 결과를 JSON으로 못 바꿈
원인: numpy/pandas/object 반환값 직렬화 처리 누락
조치: schema를 요약하고 JSON serializable 형태로 변환 기준을 안내
```

</details>

<details>
<summary>전문가 상세 보기</summary>

추론 entrypoint 후보:

```text
predict.py
aiu_custom/model_wrapper.py
aiu_custom/predict.py
local_serving/
run_model.py
runtest.py
serving/test script
```

inferencetest.py 기본 형태:

```text
req_url = ""
input_example.json 로드
requests.post(req_url, headers=headers, data=req_msg)
```

</details>

<details>
<summary>Safety 규칙 보기</summary>

- secret 또는 개인정보가 포함된 입력 예제를 그대로 출력하지 않는다.
- 추론 결과가 길면 status_code와 응답 schema 중심으로 요약한다.
- 외부 LLM endpoint 호출이 필요한 경우 endpoint와 인증 설정 존재 여부를 먼저 확인한다.
- 사용자가 별도로 요청하지 않는 한 native executable 실행 명령을 안내하지 않는다.
- `predict_2.py` 같은 별도 추론 파일을 생성하지 않는다.

</details>
