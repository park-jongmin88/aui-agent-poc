# custom_code_sample

## 타입
**RUN_CODE** — 개발자가 직접 작성한 학습 코드(.py)가 있는 케이스

## 설명
로컬에서 개발/테스트가 완료된 SVM 분류 모델 코드입니다.
이 코드를 기반으로 MLflow 등록용 run.py를 생성합니다.

## 파일 구성
| 파일 | 설명 |
|---|---|
| `train.py` | SVM 학습 코드 (prepare_data, build_model, train_model, evaluate 함수 포함) |

## 예상 init 모드
- **모드**: RUN_CODE
- **프레임워크**: custom
- **자동 생성**: 기존 함수명 감지 후 힌트 삽입

## 작업 가이드
1. `init` 실행 → run.py 생성 (train.py 함수들 참조 힌트 포함)
2. 섹션 3~5에서 train.py의 함수를 직접 연결
3. `validate` → `train`

## 주요 함수
- `prepare_data()` → 데이터 로드/전처리
- `build_model()` → SVM 모델 생성
- `train_model()` → 학습
- `evaluate()` → 평가
