"""
rag 에셋 - 질문 관련 문서를 검색해 ctx["context"] 에 채운다.
LLM 은 이 context 를 참고자료로 받아 답변한다.

[목업 / 실제 분리]
   mode="mock"   : POC용. mocks/rag_documents.json 을 키워드 매칭으로 검색
   mode="milvus" : 실제 벡터 DB. _build_milvus / _search_milvus 의 TODO 만 채우면 전환

   build/run 은 mode 에 따라 '분기'만 한다. 실제 로직은 아래 함수에 분리되어 있다.
"""

import mlflow

NAME = "rag"


def build(conn: dict):
    """mode 에 따라 목업/실제 리소스를 준비한다."""
    mode = (conn or {}).get("mode", "mock")
    if mode == "milvus":
        return _build_milvus(conn)
    return _build_mock(conn)


@mlflow.trace(name="asset.rag", span_type="RETRIEVER")
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
    """Milvus 컬렉션 + 임베딩 모델을 준비한다.

    실제 컬렉션 스키마 (iflow_aiu_collection, default DB):
        id(Int64) / text(VarChar) / metadata(JSON) / vector(FloatVector 1024)
        metric_type = L2  (인덱스에서 자동으로 읽는다)

    conn 예시 (config.py ASSET_CONN["rag"]):
        {
          "mode": "milvus",
          "uri":        "<MILVUS_URI>",      # 예: http://milvus-host:19530
          "user":       "<MILVUS_USER>",
          "password":   "<MILVUS_PASSWORD>",
          "db_name":    "default",
          "collection": "iflow_aiu_collection",
          "top_k":      3,
          "embed_model":"<임베딩 모델명>",     # 적재 때와 동일해야 함 (아래 TODO 확인)
        }
    """
    from pymilvus import connections, Collection

    connections.connect(
        alias="aiu_rag",
        uri=conn.get("uri", ""),
        user=conn.get("user", ""),
        password=conn.get("password", ""),
        db_name=conn.get("db_name", "default"),
    )
    coll = Collection(conn.get("collection", "iflow_aiu_collection"), using="aiu_rag")
    coll.load()

    # 인덱스에서 metric_type 을 자동으로 읽는다 (이 컬렉션은 L2). 못 읽으면 L2 기본.
    try:
        metric = coll.indexes[0].params.get("metric_type", "L2")
    except Exception:
        metric = "L2"

    embed = _make_embedder(conn)

    return {
        "mode":   "milvus",
        "coll":   coll,
        "metric": metric,
        "top_k":  (conn or {}).get("top_k", 3),
        "embed":  embed,
    }


def _make_embedder(conn: dict):
    """query 를 1024 차원 벡터로 바꾸는 임베딩 함수를 만든다.

    ============================ TODO: 임베딩 모델 확인 ============================
    iflow_aiu_collection 은 1024 차원으로 적재돼 있다. 검색 시에도 '적재 때와
    동일한 임베딩 모델' 을 써야 결과가 정확하다. (모델이 다르면 차원이 같아도
    벡터 공간이 달라 검색 품질이 떨어진다.)

    현재는 가장 흔한 1024 차원 모델인 BAAI/bge-m3 를 기본값으로 채워둠.
    => 적재 파이프라인(iflow) 담당자에게 실제 임베딩 모델을 확인해서 맞출 것.
       - 사내 gateway(llm.com)에 임베딩 엔드포인트가 있으면 그쪽일 가능성도 있음.
    ============================================================================
    """
    model_name = (conn or {}).get("embed_model", "BAAI/bge-m3")

    # 기본: sentence-transformers 로 로컬 임베딩 (bge-m3 는 1024 차원)
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(model_name)

        def embed(text: str):
            vec = _model.encode([text], normalize_embeddings=True)[0]
            return vec.tolist()

        return embed
    except Exception as e:
        # sentence-transformers 가 없거나 모델 로드 실패 시, 명확히 알린다.
        # (gateway 임베딩 API 를 쓰는 경우 여기서 그 호출로 교체하면 됨)
        raise NotImplementedError(
            f"임베딩 모델 준비 실패({model_name}): {e}. "
            "requirements 에 sentence-transformers 추가 또는 embed_model 확인 필요."
        )


def _search_milvus(query: str, resource) -> str:
    """query 를 임베딩해 벡터 검색 후 상위 문서 본문(text)을 잇는다."""
    vec = resource["embed"](query)
    res = resource["coll"].search(
        data=[vec],
        anns_field="vector",                       # 스키마의 벡터 필드명
        param={"metric_type": resource["metric"]}, # 이 컬렉션은 L2 (인덱스에서 읽음)
        limit=resource["top_k"],
        output_fields=["text"],                    # 본문 필드
    )
    hits = []
    for h in res[0]:
        try:
            hits.append(h.entity.get("text"))
        except Exception:
            pass
    return "\n".join(t for t in hits if t)
