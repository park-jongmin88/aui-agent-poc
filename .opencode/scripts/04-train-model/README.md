# 04 Train Model / Selected Model Build

Skill folder:
`../../skills/04-agent-mlflow-skill-train-model`

Scripts:

- `prepare_selected_model.py`
- `run_training.py`
- `adapt_ai_studio.py`

Responsibility:

- 입력 케이스 감지 (모델만/자료만/둘다) — `--train`/`--register` 로 '둘다' 선택
- 기존 `runtest.py` 를 읽기 전용으로 참조, 선택 모델 기준 `runtest_2.py` 생성
- 템플릿 복사 후 작업 폴더 구성:
  - `source/` (입력 원본) 와 `saved_model/` (등록될 결과) 분리
  - `aiu_custom/`, `config/`, `local_serving/` 준비
  - `requirements.txt` (기본 + kind별 CPU 프레임워크), `README.md` 자동 생성
- 템플릿의 샘플 `data/` 와 `requirements.txt` 는 복사하지 않음
- 확정 entrypoint 실행 (`run_training.py`)
