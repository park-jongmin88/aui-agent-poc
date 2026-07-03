# Ai Studio

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
   .opencode/는 스킬 번들이므로 분석하지 않습니다.
   case 1: 학습 코드 있음 -> 프레임워크 템플릿 변환 안내
   case 2: Pre-trained 모델 파일만 있음 -> 모델 선택
   case 3: 모델 없음 -> 샘플 선택

2. 모델 있음
   선택한 워크스페이스 루트/data 모델 목록을 번호로 보여줍니다.
   사용자는 번호 또는 경로로 사용할 모델을 선택합니다.
   자연어로도 선택할 수 있습니다. 예: "첫 번째 모델", "파이토치 모델", "data/... 모델 사용".
   모델 목록이 보이는 상태에서 숫자 키를 누르면 TODO 단계가 아니라 모델 번호 선택으로 처리합니다.
   모델 번호 선택 직후 2번 모델 선택 스크립트를 실행해 선택 모델을 고정합니다.
   실행 명령: python .opencode/scripts/02-model-select/select_model.py --project . --model <번호|경로>
   예: python .opencode/scripts/02-model-select/select_model.py --project . --model 1
   PowerShell 경로 예: python .opencode/scripts/02-model-select/select_model.py --project . --model 'data\pytorch_cnn\cnn_model.pt'
   경로 기준: Windows PowerShell에서 선택한 워크스페이스 루트 기준 상대경로만 사용합니다.
   절대경로는 입력하지 않습니다.
   모델 선택 직후에는 멈춥니다.
   3~7번은 자동 실행하지 않고 사용자가 해당 숫자를 선택했을 때만 1개씩 실행합니다.
   템플릿 변환은 사용자가 4번을 선택했을 때 별도로 실행합니다.
   data/ 원본에는 생성하지 않습니다.

3. 모델 없음
   Ai Studio에서 샘플 선택: 1 sklearn / 2 pytorch / 3 tensorflow
   숫자 키 1/2/3을 누르면 해당 샘플을 바로 선택합니다.
   자연어로 "sklearn 샘플", "파이토치 샘플", "tensorflow 샘플"처럼 요청해도 됩니다.
```
