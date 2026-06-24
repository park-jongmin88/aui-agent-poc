# 오늘 변경 내용

- 셀프 judge 제거 (assets/judge.py 삭제)
- model_wrapper / client / config 에서 judge 분기·turns 수집 삭제
- judge_eval.py (make_judge 정석 평가 스크립트) 추가
- judge 5등급 자연어 평가로 전환 반영
- judge.py 프롬프트 중괄호 이스케이프 처리 (KeyError 해결)
- judge "결과 없음" 진단 강화 처리
- client 요청 전송 surrogate 방어 추가
- 프롬프트 캐싱 반영
- 콜드스타트 워밍업 반영
- agent_flow.png 다이어그램 추가 (docs/ → root 이동)
- AIU_AGENT_POC_SUMMARY.md 최신화 반영
