# 05 Inference Test

Skill folder:
`../../skills/06-agent-mlflow-skill-inference-test`

Scripts:

- `test_inference.py`

Generated runtime entrypoint:

- `inferencetest.py`

Responsibility:

- 선택 모델 기준 원격 추론 계약 점검
- `input_example.json` 기반 입력/출력 schema 확인
- 원격 `:predict` URL HTTP POST 확인
- `predict_2.py`는 생성하지 않고 `inferencetest.py`만 사용
