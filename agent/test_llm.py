"""
==============================================================================
 LLM 통신 단독 테스트
==============================================================================

 [목적]
   서빙 환경에서 LLM(Qwen) 통신이 정상인지 단독으로 확인한다.
   서빙/등록과 무관하게 call_llm() 만 직접 호출.

 [실행]
   python agent/test_llm.py

 [판단]
   답변이 출력되면        → LLM 통신 정상 (문제는 응답 가공 단계)
   연결/타임아웃 오류면   → LLM 통신 문제 (base_url / 방화벽 확인)
==============================================================================
"""

from agent import call_llm


# ── LLM 연결 정보  ← 실제 값으로 채운다
conn = {
    "base_url":    "http://qwen.internal:8000/v1",   # 실제 값
    "api_key":     "not-needed",
    "model":       "qwen2.5-7b-instruct",
    "temperature": 0.2,
}

msg = [{"role": "user", "content": "안녕"}]

print("=" * 50)
print(" LLM 통신 테스트")
print("=" * 50)
print(f"  base_url : {conn['base_url']}")
print(f"  model    : {conn['model']}")
print("-" * 50)

try:
    answer = call_llm(msg, conn)
    print("  [성공] LLM 응답:")
    print(f"  {answer}")
except Exception as e:
    print(f"  [실패] {type(e).__name__}: {e}")

print("=" * 50)
