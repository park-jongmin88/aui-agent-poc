# sklearn_sample

## 타입
**DATA_ONLY** — CSV 데이터 파일만 있는 케이스

## 설명
분류(Classification) 문제용 샘플 데이터셋입니다.
scikit-learn의 `make_classification`으로 생성된 합성 데이터로,
8개 피처와 이진 타겟(0/1)으로 구성됩니다.

## 파일 구성
| 파일 | 설명 |
|---|---|
| `classification_data.csv` | 학습 데이터 (500행 x 9열, 마지막 열=target) |

## 예상 init 모드
- **모드**: DATA_ONLY
- **프레임워크**: sklearn
- **자동 생성**: 데이터 로드(섹션 3) 자동 생성, 모델 정의(섹션 4) TODO

## 작업 가이드
1. `init` 실행 → run.py 생성
2. 섹션 4에서 사용할 모델 선택 (기본: RandomForestClassifier)
3. `validate` → `train`
