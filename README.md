# AI-Studio 3.0 GenAI Agent (메뉴구조 개선안)

`gen-ai-agent-gateway` POC 검증을 기반으로, AI-Studio 3.0 메뉴구조 개선안의
기능들을 하나씩 부분 POC 로 만들어보는 프로젝트.

<br>

## 사용법

```bash
python main.py
```

실행하면 기능 목록이 번호로 뜨고, 선택하면 해당 기능이 동작한다.
아직 구현 안 된 기능은 계획(PLAN.md) 안내만 출력한다.

<br>

## 구조

```
main.py                진입점 - 기능 리스트업 + 번호선택 + 실행
<기능폴더>/PLAN.md       그 기능의 설계/계획 정리
<기능폴더>/run.py        실제 구현 코드 (아직 없으면 "준비중")
```

각 기능 폴더는 나중에 독립적으로도 쓸 수 있게 구성한다.

<br>

## 기능 목록

| # | 기능 | 폴더 | 상태 |
|---|------|------|------|
| 1 | Static Endpoint 생성 | `static_endpoint/` | 계획 |
| 2 | 통합 Hub / MLflow Spoke 연동 | `hub_spoke/` | 계획 |
| 3 | Langflow Import (유형1) | `langflow_import/` | 계획 |
| 4 | 모델 등록 (유형2: AIU IDE) | `model_register/` | 계획 |
| 5 | 서빙 등록 (Inference/Custom LLM) | `serving/` | 계획 |
| 6 | Evaluation / Trace 모니터링 | `evaluation/` | 계획 |
| 7 | Dataset 관리 | `dataset_builder/` | 계획 |
| 8 | Augmentation (증강) | `augmentation/` | 계획 (후순위) |
| 9 | Key / 보안 관리 | `access_control/` | 계획 (후순위) |

<br>

## 개선안 배경 (요약)

1. 사용자 중심 직관적 Navigating UI 설계
2. 고도화된 Static Endpoint 배포 — 레거시 단절 없는 전사적 AI Serving 엔진
3. 통합 Hub(E2E 가시성) + MLflow Spoke(모델 유형별 상세분석) 연동

사용자 시나리오:
```
유형1(Langflow export json) / 유형2(AIU IDE)
   → MLflow 등록 → 서빙 → Static Endpoint → Evaluation(A/B Test, Trace)
```

모델 유형: 순수 ML / ML+LLM / LLM / 시스템기반 / Dedicated LLM

<br>

## 우선순위 제안

- **바로 가능**: Static Endpoint, Evaluation/Trace 고도화, Dataset(CSV 우선)
- **중간 난이도**: Langflow Import, Hub/Spoke 연동, 서빙 확대
- **후순위**: Augmentation(복잡도 높음), Key/보안 관리(보안 정책 확인 필요)
