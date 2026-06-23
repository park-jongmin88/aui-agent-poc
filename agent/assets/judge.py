"""
judge 에셋 [확장 템플릿] - 생성된 답변을 평가해 ctx["score"] 에 채운다.
사용하려면: ENABLED_ASSETS 에 "judge" 추가 + ASSET_CONN["judge"] 채우기 + 아래 TODO 구현.
보통 파이프라인 맨 뒤(LLM 다음)에 둔다.
"""

NAME = "judge"


def build(conn: dict):
    """평가용 LLM/기준 등을 준비한다. (conn: {base_url, model, criteria})"""
    # TODO 평가 체인 준비해서 반환
    return {"conn": conn}


def run(ctx: dict, resource) -> dict:
    """ctx["answer"] 를 평가해 ctx["score"] 에 넣는다. (JUDGE 단계)"""
    # TODO 평가 구현 후 ctx["score"] 채우기
    return ctx
