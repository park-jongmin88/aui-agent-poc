# 03 Environment Check

Skill folder:
`../../skills/03-agent-mlflow-skill-environment-check`

Scripts:

- `check_environment.py`
- `response_speed_check.py`
- `apply_index_ignore.py`

Required files:

- `requirements.required.txt` - every generated workspace `requirements.txt` starts from these required packages

Responsibility:

- Python 버전 확인
- 워크스페이스 루트 `requirements.txt`가 없으면 생성하고 패키지 상태 확인
- 로컬 dependency 설치는 자동 실행하지 않음
- `.env`의 MLflow 5개 값 상태 확인
- 폐쇄망/Windows 응답 속도 진단
- `.opencode/`, `.opencode/node_modules/`, 생성물, 모델 파일 인덱싱 제외 적용
