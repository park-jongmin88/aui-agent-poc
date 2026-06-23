"""
rag 에셋 - 질문 관련 문서를 검색해 ctx["context"] 에 채운다.
LLM 은 이 context 를 참고자료로 받아 답변한다.

[목업 / 실제 분리]
   mode="mock"   : POC용. mocks/rag_documents.json 을 키워드 매칭으로 검색
   mode="milvus" : 실제 벡터 DB. _build_milvus / _search_milvus 의 TODO 만 채우면 전환

   build/run 은 mode 에 따라 '분기'만 한다. 실제 로직은 아래 함수에 분리되어 있다.
"""

NAME = "rag"


def build(conn: dict):
    """mode 에 따라 목업/실제 리소스를 준비한다."""
    mode = (conn or {}).get("mode", "mock")
    if mode == "milvus":
        return _build_milvus(conn)
    return _build_mock(conn)


def run(ctx: dict, resource) -> dict:
    """query 로 검색해 ctx["context"] 를 채운다. (목업/실제 출력 형태 동일: 문자열)"""
    if resource["mode"] == "milvus":
        ctx["context"] = _search_milvus(ctx["query"], resource)
    else:
        ctx["context"] = _search_mock(ctx["query"], resource)
    return ctx


# =============================================================================
# [목업] mode="mock" - POC용. Artifact 의 json 을 키워드 매칭으로 검색
# =============================================================================

def _build_mock(conn: dict):
    """목업 문서(json)를 읽어 둔다. (conn: {mock_path, top_k})"""
    import json
    with open(conn["mock_path"], encoding="utf-8") as f:
        docs = json.load(f)["documents"]
    return {"mode": "mock", "docs": docs, "top_k": (conn or {}).get("top_k", 3)}


def _search_mock(query: str, resource) -> str:
    """질문에 등장하는 키워드로 문서를 매칭해 상위 top_k 본문을 잇는다."""
    q = (query or "").lower()
    hits = [d["text"] for d in resource["docs"]
            if any(k.lower() in q for k in d.get("keywords", []))]
    return "\n".join(hits[:resource["top_k"]])


# =============================================================================
# [실제] mode="milvus" - TODO: Milvus 연결되면 이 두 함수만 채운다
# =============================================================================

def _build_milvus(conn: dict):
    """Milvus 컬렉션/임베딩을 준비한다. (conn: {host, port, collection, top_k})"""
    # TODO Milvus 연결
    #   from pymilvus import connections, Collection
    #   connections.connect(host=conn["host"], port=conn["port"])
    #   coll = Collection(conn["collection"]); coll.load()
    #   return {"mode": "milvus", "coll": coll, "top_k": conn.get("top_k", 3),
    #           "embed": <임베딩 함수>}
    raise NotImplementedError("Milvus 연결 미구현 - ASSET_CONN['rag']['mode']='mock' 사용")


def _search_milvus(query: str, resource) -> str:
    """query 를 임베딩해 벡터 검색 후 상위 문서 본문을 잇는다."""
    # TODO 실제 벡터 검색
    #   vec = resource["embed"](query)
    #   res = resource["coll"].search(
    #       data=[vec], anns_field="embedding", param={"metric_type": "COSINE"},
    #       limit=resource["top_k"], output_fields=["text"])
    #   return "\n".join(h.entity.get("text") for h in res[0])
    raise NotImplementedError("Milvus 검색 미구현 - ASSET_CONN['rag']['mode']='mock' 사용")
