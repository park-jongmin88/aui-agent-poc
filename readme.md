# AIU DeepAgent (POC)

ML/DL 개발자를 위한 AI STUDIO 프로세스 CLI 자동화 — LangChain DeepAgents 기반.

## Quick Start
1. `quickstart.bat` 실행 (가상환경 + 의존성 설치)
2. `.env` 파일의 TODO 항목 작성 (사내 LLM, MLflow 정보)
3. `.venv\Scripts\activate` → `python main.py`

## 구조
```
main.py          DeepAgent 진입점 (CLI 대화 루프)
agent.md         프로젝트 정의 (항상 로드)
skills/          5개 스킬 (init / validate / train / deploy / predict)
template/        run.py 베이스 템플릿 (9-섹션 표준)
setting/         config.json, requirements.txt
model/           모델 폴더 목록 - 폴더 안 파일은 run.py 생성용 기초 자료 (동작 샘플 3종 포함)
model_result/    학습 결과물
local_test/      MLflow 등록 모델 로컬 검증
.env             사내 LLM / MLflow / MODEL_NO 설정
```

## 스킬 사용 예
```
aiu> my_model 폴더 자료로 run.py 만들어줘  → init
aiu> 내 run.py 양식 맞는지 봐줘   → validate
aiu> sklearn_sample 학습해줘      → train
aiu> 방금 등록한 모델 추론 테스트  → predict
```
