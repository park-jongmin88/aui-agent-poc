"""
rag 에셋 [확장 템플릿] - 검색 결과를 ctx["context"] 에 채운다.
사용하려면: ENABLED_ASSETS 에 "rag" 추가 + ASSET_CONN["rag"] 채우기 + 아래 TODO 구현.
"""

NAME = "rag"


def build(conn: dict):
    """벡터 DB 클라이언트 등을 준비한다. (conn: {vector_db, host, port, collection, top_k})"""
    # TODO 벡터 DB 연결 객체 생성해서 반환
    return {"conn": conn}


def run(ctx: dict, resource) -> dict:
    """query 로 문서를 검색해 ctx["context"] 에 넣는다. (RETRIEVER 단계)"""
    # TODO 검색 구현 후 ctx["context"] 채우기
    # ctx["context"] = search(ctx["query"], resource)
    return ctx
