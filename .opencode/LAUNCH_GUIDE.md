# Launch Guide

```text
Ai Studio - 7단계

실행 기준:
   Windows PowerShell에서 사용자가 선택한 워크스페이스 루트로 이동한 뒤 실행합니다.
   예: cd '<선택한 프로젝트 경로>'
   스크립트는 항상 --project . 로 실행합니다.
   모델 경로는 선택한 워크스페이스 기준 상대경로만 사용합니다.
   절대경로(C:\..., /Users/..., /home/...)는 사용하지 않습니다.

1. 먼저 워크스페이스를 분석합니다.
   model_found: true | false
   case 1: 학습 코드 있음 -> 프레임워크 템플릿 변환 안내
   case 2: Pre-trained 모델 파일만 있음 -> 모델 선택
   case 3: 모델 없음 -> 샘플 선택

2. data/ 폴더를 꼭 생성합니다.
   모델은 data/ 폴더에 넣고 시작합니다.

3. 모델 선택
   숫자로 선택 가능:
   1, 2, 3 ...

   자연어로도 선택 가능:
   "첫 번째 모델", "파이토치 모델", "data/... 사용"

   숫자 1번 선택 시 실행:
   python .opencode/scripts/02-model-select/select_model.py --project . --model 1

   PowerShell 경로 예:
   python .opencode/scripts/02-model-select/select_model.py --project . --model 'data\pytorch_cnn\cnn_model.pt'

4. 모델 있음 7단계
   1 모델 목록 확인
   2 모델 선택
   3 환경 검증 (사용자 선택)
   4 템플릿 변환 (사용자 선택)
   5 원격 MLflow 등록 실행 (사용자 선택)
   6 추론 테스트 (사용자 선택)
   7 오류 재실행 (사용자 선택)
```

모델 목록이 표시된 상태에서 숫자 키를 누르면 TODO 단계가 아니라 모델 번호 선택으로 처리합니다.
2번 모델 선택 후에는 자동으로 3~7번을 실행하지 않습니다.
각 단계는 사용자가 해당 숫자를 선택했을 때만 1개씩 실행합니다.
secret 값은 출력하지 않고 `set`, `empty`, `missing` 상태만 표시합니다.
