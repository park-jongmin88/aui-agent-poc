---
name: init
description: "workspace/models/ 하위 폴더를 분석해 workspace/run.py 를 생성한다. 작업 순서 1단계. 다음과 같은 요청에 사용: '준비해줘', '시작해줘', '폴더 분석해줘', '작업 시작', '학습 준비해줘', 'sklearn_sample로 시작해줘', '모델 폴더 선택해줘', '어떤 파일이 있는지 봐줘', '처음부터 시작할게', '1번 폴더로 해줘'."
---
# init - 작업 폴더 분석 및 run.py 생성

## 개념
workspace/models/ 의 폴더 안 파일들은 run.py 를 만들기 위한 기초 자료다.
최종 결과물은 항상 workspace/run.py 하나다.

## 절차
1. 작업 폴더가 지정되지 않았으면 skills/init/scripts/analyze_folder.py 를 인자 없이 실행
   → 번호가 붙은 폴더 목록을 보여주고 사용자에게 번호로 선택받기
2. 폴더 번호 또는 이름을 인자로 analyze_folder.py 실행 → 파일 분석 결과 확인
3. 분석 결과(mode, framework, 파일 목록)를 사용자에게 보고하고 진행 여부 확인
4. workspace/run.py 가 이미 있으면 덮어쓸지 확인
5. 분석 결과에 따라 workspace/run.py 생성:
   - workspace/templates/run.py 를 기반으로
   - MODEL_NAME을 폴더명으로 치환
   - 파일 목록에 맞게 섹션 3~5 작성 (데이터 로드, 모델 로드/정의, 학습)
   - TODO 주석으로 사용자 확인 필요 항목 표시
6. 생성 완료 후 validate 실행 권장

## 주의
- workspace/templates/ 원본은 절대 수정하지 않는다
- 기초 자료(원본 데이터, 기존 코드)는 삭제하거나 수정하지 않는다
