---
name: deploy
description: "학습/추론이 끝난 모델을 AI Studio 포탈에 배포해 Endpoint를 생성한다. 작업 순서 7단계 (predict 후). 다음과 같은 요청에 사용: '배포해줘', '배포', '엔드포인트 생성', '서비스 배포', '포탈에 올려줘' 영어/추가 표현: '디플로이', 'deploy', '배포하자', '프로덕션', '실서버 배포', '서비스화', '운영 배포'."
---
# deploy - AI Studio Endpoint 배포

## 필요 (사전 조건)
- MLflow에 모델이 등록되어 있어야 함 (status=predicted)
- config.json 의 aistudio 섹션 설정 (api_url, project_id)
- system_key 는 선택 (고정값, 없으면 생략)

## 경로 기준 (중요)
- 모든 경로/정보는 스크립트가 config + 상태에서 자동 수집한다.
- 에이전트가 직접 project_id나 모델명을 추론하지 않는다.

## 게이트 조건
- status=predicted 없으면 차단
- "먼저 predict(추론)를 실행해주세요" 안내

## 배포 흐름
1. MLflow 모델 등록 확인 (model_name, model_version)
2. config(aistudio) + 상태에서 정보 수집
   - project_id, api_url, system_key ← config.json
   - model_name, model_version ← .aiu_state.json
3. requirements.txt 내용을 dependency로 로드
4. 기본 리소스 설정 (필요 시 변경 여부 질문)
5. Endpoint 생성 API 호출
6. RUNNING 상태까지 폴링
7. Endpoint URL 반환 → 상태에 저장

## 스크립트 호출 방식
```
python skills/deploy/scripts/deploy_run.py [폴더명]
```
- `deploy_run.py`: 진입점 (게이트 → 정보수집 → 배포 → 상태저장)
- `deploy_client.py`: AI Studio API 클라이언트 (AIStudioAPIClient)

## 배포 후
- Endpoint URL이 `.aiu_state.json` 의 endpoint_url 에 저장됨
- predict ② (Endpoint 추론)에서 이 URL을 자동 사용
- "엔드포인트 추론 테스트해줘" 로 검증

## 주의 (POC)
- 실제 AI Studio API 스펙에 맞춰 deploy_client.py 의 TODO(경로/응답 필드)를 채워야 동작합니다.
- 현재는 배포 흐름 골격이 구현되어 있습니다.
- API 주소/키는 config.json 의 aistudio 섹션에서 설정합니다.
