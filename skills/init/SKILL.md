---
name: init
description: "모델 폴더의 기초 자료(데이터, 기존 코드, 모델 파일 등)를 분석해 표준 run.py를 생성한다. 자료가 없으면 workspace/templates/run.py를 복사해 시작점을 만든다. 초기화, 새 모델 시작, run.py 만들기 요청 시 사용."
---
# init - 기초 자료 기반 run.py 생성

## 개념
모델 폴더 안의 모든 파일은 run.py를 만들기 위한 **기초 자료**다.
최종 결과물은 항상 9-섹션 표준을 따르는 run.py 하나다.

## 절차
1. 대상 폴더를 확인한다. 지정이 없으면 workspace/models/ 하위 폴더 목록을 보여주고 선택받는다.
2. 폴더 안의 자료를 전부 스캔하고 유형을 파악한다:
   - 데이터 파일 (csv, parquet, npy 등) → 학습 데이터 후보
   - 기존 스크립트/노트북 → 변환할 코드 소스
   - 모델 파일 (pkl, pt, h5 등) → 이미 완성된 모델일 가능성
   - run.py 가 이미 있으면 → 생성 대신 validate를 권한다
3. 자료에 대해 사용자와 대화로 확인한다 (예: 타깃 컬럼, 사용할 프레임워크, 어떤 파일이 최신인지).
4. workspace/templates/run.py 의 9-섹션 구조를 기준으로, 자료를 반영한 run.py를 작성한다:
   - 자료가 충분하면 → 섹션을 실제 코드로 채움
   - 자료가 없거나 빈 폴더면 → workspace/templates/run.py 복사 후 TODO 항목 안내
5. 작성/수정 전에는 반드시 사용자에게 내용을 보여주고 동의받는다.
6. 완료 후 validate 실행을 권한다.

## 주의
- workspace/templates/ 원본은 절대 수정하지 않는다.
- 폴더의 기초 자료(원본 데이터, 기존 코드)는 삭제하거나 수정하지 않는다.
- 참고용 동작 샘플: workspace/models/sklearn_sample, pytorch_sample, tensorflow_sample
