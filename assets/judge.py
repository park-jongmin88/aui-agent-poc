"""
judge 에셋 - 세션이 끝나면 생성된 답변(들)을 평가한다.

[다른 에셋과 다른 점]
   prompt/rag/tool/llm 은 매 대화마다 파이프라인(run)에서 돈다.
   judge 는 '세션 끝에 한 번' 도는 사후 평가라, 파이프라인이 아니라
   별도 진입점(evaluate)으로 호출된다. (predict 의 mode="judge")
   따라서 ENABLED_ASSETS 에는 넣지 않는다.

[평가 방식] LLM-as-a-judge
   생성에 쓰는 LLM 으로 답변을 채점한다. (POC: 같은 모델 재사용)
   평가 모델을 분리하려면 config 의 JUDGE_CONN 만 다른 값으로 바꾸면 된다.

[평가 기준] 각 1~5점
   - accuracy   : 질문에 맞고 정확한가
   - helpfulness: 실제로 도움이 되는가
   - clarity    : 이해하기 쉬운가

[목업 / 실제 분리]
   mode="mock" : LLM 호출 없이 고정 점수 반환 (구조 검증용)
   mode="llm"  : 실제 평가 LLM 호출 (_evaluate_llm)
"""

import json
import mlflow

NAME = "judge"

# 평가 결과를 JSON 으로만 받기 위한 시스템 프롬프트
_JUDGE_SYSTEM = (
    "너는 답변 품질을 평가하는 채점자다. "
    "주어진 '질문'과 '답변'을 보고 아래 세 기준을 각각 1~5점으로 평가한다.\n"
    "- accuracy: 질문에 맞고 정확한가\n"
    "- helpfulness: 실제로 도움이 되는가\n"
    "- clarity: 이해하기 쉬운가\n"
    "반드시 아래 JSON 형식으로만 답한다. 다른 말은 절대 쓰지 않는다.\n"
    '{{"accuracy": 정수, "helpfulness": 정수, "clarity": 정수, "reason": "간단한 이유"}}'
)


def build(conn: dict):
    """평가용 LLM 체인을 준비한다. (conn: {mode, base_url, model, api_key})"""
    mode = (conn or {}).get("mode", "mock")
    if mode == "llm":
        return _build_llm(conn)
    return {"mode": "mock"}


def evaluate(items: list, resource) -> dict:
    """
    세션의 (질문, 답변) 목록을 받아 평가 결과를 반환한다.
    items: [{"query": ..., "answer": ...}, ...]
    return: {"per_turn": [...], "avg": {...}, "count": n}
    """
    if not items:
        return {"per_turn": [], "avg": {}, "count": 0}

    if resource["mode"] == "llm":
        per_turn = [_evaluate_llm(it, resource) for it in items]
    else:
        per_turn = [_evaluate_mock(it) for it in items]

    # 평균 계산
    keys = ("accuracy", "helpfulness", "clarity")
    avg = {}
    for k in keys:
        vals = [t["scores"].get(k, 0) for t in per_turn if isinstance(t.get("scores"), dict)]
        avg[k] = round(sum(vals) / len(vals), 2) if vals else 0
    return {"per_turn": per_turn, "avg": avg, "count": len(per_turn)}


# =============================================================================
# [목업] mode="mock" - LLM 없이 고정 점수 (구조 검증용)
# =============================================================================

def _evaluate_mock(item: dict) -> dict:
    return {
        "query":  item.get("query", ""),
        "scores": {"accuracy": 4, "helpfulness": 4, "clarity": 4},
        "reason": "(목업) 고정 점수",
    }


# =============================================================================
# [실제] mode="llm" - 평가 LLM 호출. POC 는 생성과 같은 모델 재사용
# =============================================================================

def _build_llm(conn: dict):
    """평가용 ChatOpenAI 체인 준비. (conn: {base_url, model, api_key})"""
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser

    model = ChatOpenAI(
        model=conn["model"],
        api_key=conn.get("api_key", ""),
        base_url=conn["base_url"],
        temperature=0,
        max_retries=2,
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", _JUDGE_SYSTEM),
        ("user", "[질문]\n{query}\n\n[답변]\n{answer}"),
    ])
    return {"mode": "llm", "chain": prompt | model | StrOutputParser()}


@mlflow.trace(name="judge.evaluate_turn", span_type="LLM")
def _evaluate_llm(item: dict, resource) -> dict:
    """한 턴을 평가 LLM 으로 채점한다. JSON 파싱 실패 시 0점 처리."""
    query = item.get("query", "")
    answer = item.get("answer", "")
    raw = resource["chain"].invoke({"query": query, "answer": answer})
    scores, reason = _parse_scores(raw)
    return {"query": query, "scores": scores, "reason": reason}


def _parse_scores(raw: str):
    """평가 LLM 응답(JSON 문자열)에서 점수와 이유를 뽑는다."""
    text = (raw or "").strip()
    # ```json ... ``` 같은 코드펜스 제거
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    try:
        data = json.loads(text)
        scores = {
            "accuracy":    int(data.get("accuracy", 0)),
            "helpfulness": int(data.get("helpfulness", 0)),
            "clarity":     int(data.get("clarity", 0)),
        }
        return scores, str(data.get("reason", ""))
    except Exception:
        return {"accuracy": 0, "helpfulness": 0, "clarity": 0}, "[파싱 실패] " + text[:100]
