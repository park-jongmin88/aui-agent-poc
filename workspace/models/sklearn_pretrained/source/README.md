# sklearn_pretrained

## 타입
**LOAD_MODEL** — 이미 학습된 sklearn 모델 파일(.pkl)이 있는 케이스

## 설명
로컬에서 미리 학습된 RandomForestClassifier 모델입니다.
이 모델을 MLflow에 등록하는 것이 목표입니다.

## 파일 구성
| 파일 | 설명 |
|---|---|
| `rf_classifier.pkl` | 학습된 RandomForest 모델 (joblib) |
| `model_info.json` | 모델 메타정보 (accuracy, 버전 등) |

## 예상 init 모드
- **모드**: LOAD_MODEL
- **프레임워크**: sklearn
- **자동 생성**: joblib.load 코드 자동 삽입, 재학습 불필요

## 작업 가이드
1. `init` 실행 → run.py 자동 생성 (모델 로드 코드 포함)
2. `validate` → 섹션 5에서 재학습 여부만 결정
3. `train` → MLflow에 등록
