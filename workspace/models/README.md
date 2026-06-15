# workspace/models/ — 작업 폴더 모음

각 폴더는 하나의 모델 작업 단위입니다.
`source/README.md` 에서 각 폴더의 상세 설명을 확인하세요.

---

## 폴더 목록

### sklearn_sample/
- **타입**: DATA_ONLY
- **내용**: CSV 분류 데이터 (500행 x 9열)
- **예상 모드**: DATA_ONLY → 데이터 로드 자동, 모델 정의 TODO
- **적합한 경우**: 데이터만 있고 처음부터 모델을 선택/학습하려는 경우

### sklearn_pretrained/
- **타입**: LOAD_MODEL
- **내용**: 학습된 RandomForest 모델 (.pkl) + 메타정보 (accuracy=0.88)
- **예상 모드**: LOAD_MODEL → joblib.load 코드 자동 생성
- **적합한 경우**: 로컬에서 학습 완료한 모델을 MLflow에 바로 등록하려는 경우

### custom_code_sample/
- **타입**: RUN_CODE
- **내용**: SVM 분류 모델 학습 코드 (.py) — prepare_data/build_model/train_model/evaluate 함수
- **예상 모드**: RUN_CODE → 기존 함수 감지 후 힌트 삽입
- **적합한 경우**: 로컬에서 개발/테스트 완료된 코드를 MLflow에 연동하려는 경우

### multifile_sample/
- **타입**: 혼합 (CSV + .py)
- **내용**: 주택 가격 회귀 데이터 + 전처리 코드 (preprocess.py)
- **예상 모드**: RUN_CODE (코드 파일 우선)
- **적합한 경우**: 데이터와 전처리 코드가 함께 있는 경우, 회귀 모델

### template_only/
- **타입**: TEMPLATE
- **내용**: 빈 폴더 (처음부터 작성)
- **예상 모드**: TEMPLATE → 기본 템플릿 + TODO 6개
- **적합한 경우**: 처음부터 새 모델을 설계하는 경우

### pytorch_sample/
- **타입**: TEMPLATE
- **내용**: PyTorch 학습 시작용 빈 폴더
- **예상 모드**: TEMPLATE (init 후 수동으로 torch import 변경 필요)
- **적합한 경우**: PyTorch 딥러닝 모델을 MLflow에 등록하려는 경우

### tensorflow_sample/
- **타입**: TEMPLATE
- **내용**: TensorFlow/Keras 시작용 빈 폴더
- **예상 모드**: TEMPLATE (init 후 수동으로 tf import 변경 필요)
- **적합한 경우**: TensorFlow/Keras 모델을 MLflow에 등록하려는 경우

---

## init 모드별 자동화 수준

| 모드 | 트리거 | 자동화 수준 | 수동 작업 |
|---|---|---|---|
| LOAD_MODEL | .pkl/.joblib/.h5/.keras 파일 | ★★★ 거의 완전 자동 | 재학습 여부 결정 |
| RUN_CODE | .py/.ipynb 파일 | ★★☆ 함수 연결 필요 | 섹션 3~5 함수 연결 |
| DATA_ONLY | .csv/.parquet 등 | ★★☆ 데이터 로드 자동 | 모델 구조 정의 |
| TEMPLATE | 빈 폴더 | ★☆☆ 기본 틀만 | 섹션 3~5 전체 작성 |

---

## 새 모델 추가 방법

1. `workspace/models/` 아래 새 폴더 생성
2. `source/` 폴더에 원본 자료 (데이터/코드/모델파일) 복사
3. `source/README.md` 작성 (타입, 설명, 작업 가이드)
4. 에이전트에게 "새 폴더 준비해줘" 요청

## 주의사항
- `source/` 안의 원본 파일은 에이전트가 수정/삭제하지 않습니다
- `run.py` 는 init 스킬이 자동 생성합니다 (덮어쓰기 전 확인)
- `.aiu_state.json` 은 단계별 진행 상태를 저장합니다 (자동 관리)
- `workspace/templates/run.py` 는 베이스 템플릿입니다 (수정 금지)
