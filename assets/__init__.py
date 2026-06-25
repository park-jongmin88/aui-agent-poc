"""
==============================================================================
 assets - 에이전트 에셋 모듈 모음
==============================================================================
 개발자는 이 폴더에 에셋 파일 하나를 추가하는 것으로 기능을 확장한다.

 [에셋 공통 규약]  (모든 에셋 파일이 따른다)
   NAME : str                         # 에셋 이름. agent.py 의 ENABLED_ASSETS 항목과 매칭
   build(conn: dict) -> resource      # 등록/로드 시 1회. 연결정보로 준비된 객체 반환
   run(ctx: dict, resource) -> dict   # 호출 시마다. ctx(대화 맥락) 가공 후 반환

 [ctx - 파이프라인 맥락]  에셋들이 순서대로 주고받는 공용 보따리
   {
     "query":          사용자 질문,
     "system_message": 시스템 프롬프트,
     "context":        RAG 검색 결과(있으면),
     "tools_result":   Tool 실행 결과(있으면),
     "answer":         LLM 생성 답변,
     "score":          Judge 평가(있으면),
   }

 [추가 방법]  README 참고
   1. assets/<이름>.py 생성 (이 규약대로 NAME/build/run 작성)
   2. agent.py 의 ENABLED_ASSETS 리스트에 <이름> 추가
   3. 연결정보가 필요하면 agent.py 의 ASSET_CONN 에 항목 추가
==============================================================================
"""

import importlib


def new_ctx(query: str, system_message: str, prompt_id: str = "", prompt_version=None) -> dict:
    """파이프라인 맥락(ctx) 초기값을 만든다."""
    return {
        "query":          query,
        "system_message": system_message or "",
        "prompt_id":      prompt_id or "",   # client 가 고른 프롬프트 이름(서버에서 로드)
        "prompt_version": prompt_version,    # client 가 고른 버전 (None 이면 최신)
        "context":        "",
        "tools_result":   "",
        "answer":         "",
        "score":          None,
    }


def load_asset(name: str):
    """assets/<name>.py 모듈을 import 해서 반환한다. (NAME/build/run 보유 가정)"""
    return importlib.import_module(f"assets.{name}")
