# Dataset 관리 (Dataset Builder) - 계획

<br>

## 목적

원본 파일은 보존한 채, 텍스트 중심의 표준 정형 Dataset 로 변환해 저장한다.
AI-Studio 내 별도 Datasets 관리 메뉴로 구성하고, MLflow Evaluation API 로 매핑한다.

<br>

## 빌딩 파이프라인

```
① 업로드
   개별/단일 원본파일 업로드
   또는 Bulk 데이터셋 생성 (Zip 업로드)
        ↓
② 목록 확인 + 데이터 유형 선택 / 추출 규칙 설정
        ↓
③ 판단 분기
   정형/구조화 (CSV 같은 유형)
   or
   비정형 (PDF, DOC, PPT)
        ↓
④ 표준 스키마 변환
   컬럼 매핑, Chunking 방식, 오버랩 크기 설정 등
        ↓
   표 형태의 프리뷰 데이터 생성
        ↓
⑤ 프리뷰 데이터 검수 및 승인
        ↓
⑥ 분기
   증강 필요 → Augmentation 단계로 이동 (augmentation/ 참고)
   증강 불필요 → 데이터셋 등록 완료
```

<br>

## 우선순위 제안

- **정형(CSV) 처리부터** — 비정형(PDF/DOC/PPT) 파싱보다 훨씬 단순해서
  먼저 파이프라인 전체를 한 번 통과시켜보는 용도로 적합
- 비정형은 그다음 단계에서 확장

<br>

## 하고 싶은 것

- CSV 업로드 → 컬럼 매핑 → 표준 스키마 변환 → 프리뷰 → MLflow Evaluation
  Dataset 등록까지 최소 흐름 구현
- Bulk(Zip) 업로드는 개별 업로드가 된 뒤 확장

<br>

## TODO

- [ ] "표준 스키마"의 정확한 필드 정의 (텍스트 중심이라 함은 어떤 컬럼 구성인지)
- [ ] MLflow Evaluation Dataset API 조사 및 매핑 방식 확정
- [ ] CSV 우선 구현 → PDF/DOC/PPT 순으로 확장 계획
