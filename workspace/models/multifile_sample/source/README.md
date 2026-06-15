# multifile_sample

## 타입
**혼합 케이스** — CSV 데이터 + 전처리 코드(.py)가 함께 있는 케이스

## 설명
주택 가격 회귀(Regression) 예측 모델입니다.
데이터 파일과 전처리 코드가 함께 제공됩니다.

## 파일 구성
| 파일 | 설명 |
|---|---|
| `housing_data.csv` | 주택 가격 데이터 (300행, 5개 피처 + price 타겟) |
| `preprocess.py` | 데이터 전처리 유틸리티 (load_and_preprocess 함수) |

## 예상 init 모드
- **모드**: RUN_CODE (코드 파일이 우선순위)
- **프레임워크**: custom
- **자동 생성**: preprocess.py 함수 감지 후 힌트 삽입

## 작업 가이드
1. `init` 실행 → run.py 생성
2. 섹션 3에서 `preprocess.load_and_preprocess()` 연결
3. 섹션 4에서 회귀 모델 선택 (Ridge, LinearRegression 등)
4. `validate` → `train`

## 주의
- 회귀 문제이므로 accuracy 대신 RMSE/MAE 메트릭 사용 권장
- mlflow.log_metric("rmse", ...) 으로 변경 필요
