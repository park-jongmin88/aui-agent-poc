# 통합 Hub / MLflow Spoke 연동 - 계획

<br>

## 목적

통합 Hub 를 통해 파이프라인의 E2E 가시성을 확보하고, 모델 유형에 따른
특화된 상세분석은 MLflow(Spoke) 로 연동하여 사용자 경험을 최적화한다.

<br>

## 구조

```
[통합 Hub]                      [MLflow (Spoke)]
 E2E 파이프라인 상태 한눈에  →   모델 유형별 상세분석 딥링크
 (등록/서빙/평가 진행상황)        (Trace, Evaluation 상세 등)
```

- Hub 는 "지금 파이프라인이 어디까지 왔나"를 요약해서 보여주는 역할
- 상세 분석(trace 상세, evaluation 결과 등)은 MLflow 화면으로 딥링크 연결

<br>

## 하고 싶은 것

- 유형1/유형2 → 등록 → 서빙 → Endpoint → Evaluation 각 단계의 상태를
  Hub 에서 한눈에 확인
- 각 단계 클릭 시 MLflow 해당 화면(experiment, run, trace 등)으로 이동

<br>

## TODO

- [ ] Hub 에서 보여줄 "상태" 정의 (성공/실패/진행중 등 단계별 상태값)
- [ ] MLflow 각 화면의 URL 패턴 정리 (딥링크 매핑표)
- [ ] Hub API 설계 (각 단계 상태를 어디서 가져올지 - MLflow API 조회)
