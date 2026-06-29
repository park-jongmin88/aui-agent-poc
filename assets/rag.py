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
          "uri":            "<MILVUS_URI>",      # 예: http://milvus.도메인.com:19530
          "user":           "<MILVUS_USER>",
          "password":       "<MILVUS_PASSWORD>",
          "db_name":        "default",
          "collection":     "iflow_aiu_collection",
          "top_k":          3,
          "nprobe":         16,
          "embed_base_url": "<임베딩 서버>",       # 예: http://embedding.llm.도메인.com/v1
          "embed_api_key":  "<임베딩 키>",
          "embed_model":    "bge-m3",
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
        "nprobe": (conn or {}).get("nprobe", 16),   # IVF_FLAT 검색 파라미터
        "embed":  embed,
    }


def _make_embedder(conn: dict):
    """query 를 1024 차원 벡터로 바꾸는 임베딩 함수를 만든다.

    임베딩 모델: bge-m3 (1024 차원) — iflow_aiu_collection 적재 때 쓴 것과 동일.
    검색 시에도 반드시 같은 모델/서버를 써야 벡터 공간이 일치한다.

    호출 방식: OpenAI 호환 임베딩 API (/v1/embeddings).
      - 적재 때 쓴 임베딩 서버를 그대로 사용한다.
      - 이 서버는 LLM 과 도메인은 같지만 서브도메인이 분리돼 있다.
        예) LLM      http://llm.도메인.com/v1
            임베딩   http://embedding.llm.도메인.com/v1
      - torch/로컬 모델 불필요(가벼움), 적재 인프라와 벡터 일치.

    conn 에서 사용하는 값 (config.py ASSET_CONN["rag"]):
        embed_base_url : 임베딩 서버 주소 (예: http://embedding.llm.도메인.com/v1)
        embed_api_key  : 인증 키 (환경변수 주입)
        embed_model    : 모델명 (bge-m3)
    """
    base_url = (conn or {}).get("embed_base_url", "")
    api_key  = (conn or {}).get("embed_api_key", "")
    model    = (conn or {}).get("embed_model", "bge-m3")

    from openai import OpenAI
    client = OpenAI(base_url=base_url, api_key=api_key)

    def embed(text: str):
        resp = client.embeddings.create(model=model, input=text)
        return resp.data[0].embedding   # 1024 차원 벡터

    return embed


def _search_milvus(query: str, resource) -> str:
    """query 를 임베딩해 벡터 검색 후 상위 문서 본문(text)을 잇는다.

    인덱스: IVF_FLAT (nlist=128) / metric: L2
      - IVF_FLAT 은 검색 시 nprobe(뒤질 클러스터 수)가 필요하다.
        nprobe 가 클수록 정확하지만 느리다. nlist=128 기준 16 정도가 무난.
    """
    vec = resource["embed"](query)
    res = resource["coll"].search(
        data=[vec],
        anns_field="vector",                       # 스키마의 벡터 필드명
        param={
            "metric_type": resource["metric"],     # L2 (인덱스에서 읽음)
            "params": {"nprobe": resource.get("nprobe", 16)},  # IVF_FLAT 검색 파라미터
        },
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
