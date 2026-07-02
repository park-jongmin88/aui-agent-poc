"""
==============================================================================
 mlflow_inspect.py  -  MLflow 조회 헬퍼 (확인용 단독 스크립트)
==============================================================================
 프로젝트에 등록된 것들을 "조회만" 하는 도구. 등록/수정/삭제 안 함.
 현재 프로젝트 코드와 독립 — 이 파일 하나만 실행하면 됨 (영향 없음).

 조회 대상:
   1) Gateway 엔드포인트  (chat / embeddings / completions 타입별)
   2) Prompt (+ 버전)
   3) Judge / Scorer      (자동평가용, 3.13+)

 사용법:
   1. 아래 [입력] 의 MLflow 정보를 채운다 (TODO).
   2. python mlflow_inspect.py 실행.
   3. 메뉴에서 조회할 대상을 고른다.
   4. 목록에서 항목을 고르면 상세를 보여준다.

 요구: pip install mlflow   (조회만 하므로 서버 접속만 되면 됨)
==============================================================================
"""

import sys
import traceback


# #############################################################################
# [입력] ★ 여기만 채우세요
# #############################################################################

MLFLOW_TRACKING_URI = TODO   # 예: "http://mlflow.도메인.com"  (프로젝트별 주소)
MLFLOW_USERNAME     = TODO   # 인증 없으면 "" 로
MLFLOW_PASSWORD     = TODO   # 인증 없으면 "" 로
# 특정 experiment 로 좁혀 보고 싶으면 지정 (judge/scorer 조회에 사용). 없으면 "" 유지.
EXPERIMENT_NAME     = ""     # 예: "aiu-agent"  (비우면 기본/전체)


# #############################################################################
# [공통] 유틸
# #############################################################################

def _sep(title=""):
    print("\n" + "=" * 70)
    if title:
        print(f" {title}")
        print("=" * 70)


def _err(context: str, e: Exception):
    """조회 오류를 사람이 읽기 쉽게 + traceback 까지 남긴다."""
    print(f"\n[조회 오류] {context}")
    print(f"  타입 : {type(e).__name__}")
    print(f"  내용 : {e}")
    print("  ── traceback ──")
    traceback.print_exc()
    print("  ───────────────")
    # 흔한 원인 힌트
    msg = str(e).lower()
    if "connection" in msg or "refused" in msg or "timeout" in msg:
        print("  힌트: MLflow 주소/네트워크 확인 (MLFLOW_TRACKING_URI).")
    elif "401" in msg or "403" in msg or "unauthor" in msg or "permission" in msg:
        print("  힌트: 인증/권한 문제 (USERNAME/PASSWORD 또는 서버 권한).")
    elif "not found" in msg or "404" in msg:
        print("  힌트: 대상이 없거나 이 서버에 조회 API 가 없을 수 있음.")


def _setup():
    """MLflow 연결 설정 + 연결 확인. 실패하면 종료."""
    import os
    import mlflow

    if not isinstance(MLFLOW_TRACKING_URI, str) or not MLFLOW_TRACKING_URI:
        print("[중지] MLFLOW_TRACKING_URI 를 먼저 채우세요 (파일 상단 [입력]).")
        sys.exit(1)

    if isinstance(MLFLOW_USERNAME, str) and MLFLOW_USERNAME:
        os.environ["MLFLOW_TRACKING_USERNAME"] = MLFLOW_USERNAME
    if isinstance(MLFLOW_PASSWORD, str) and MLFLOW_PASSWORD:
        os.environ["MLFLOW_TRACKING_PASSWORD"] = MLFLOW_PASSWORD

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    print(f"MLflow 주소: {MLFLOW_TRACKING_URI}")
    try:
        print(f"MLflow 버전: {mlflow.__version__}")
    except Exception:
        pass

    # 연결 확인 (첫 요청은 몇 초 걸릴 수 있으므로 진행 상태를 보여준다)
    print("MLflow 연결 확인 중 ...", end=" ", flush=True)
    try:
        # 가벼운 요청으로 실제 응답 오는지 확인 (experiment 목록 1건)
        client = mlflow.MlflowClient()
        client.search_experiments(max_results=1)
        print("확인 완료 ✅", flush=True)
    except Exception as e:
        print("실패 ❌", flush=True)
        _err("MLflow 연결 확인(search_experiments)", e)
        ans = input("\n그래도 계속 진행할까요? (y/N): ").strip().lower()
        if ans != "y":
            print("중지합니다. 주소/인증을 확인하세요.")
            sys.exit(1)

    return mlflow


def _pick(items, render):
    """목록을 번호로 보여주고 하나 고르게 한다. 반환: 고른 항목 or None(뒤로)."""
    if not items:
        print("  (조회된 항목이 없습니다.)")
        return None
    for i, it in enumerate(items, 1):
        print(f"  [{i}] {render(it)}")
    print("  [0] 뒤로")
    while True:
        sel = input("  번호 선택: ").strip()
        if sel == "0":
            return None
        if sel.isdigit() and 1 <= int(sel) <= len(items):
            return items[int(sel) - 1]
        print("  올바른 번호를 입력하세요.")


# #############################################################################
# 1) Gateway 엔드포인트 조회
# #############################################################################
#
#  [중요] mlflow 의 get_deploy_client().list_endpoints() 는 옛 경로
#         (/api/2.0/endpoints/) 를 호출해서 3.x 서버에서는 404 가 난다.
#         3.x gateway 의 실제 경로는 아래와 같다 (MLflow UI 가 쓰는 경로):
#             /api/3.0/mlflow/gateway/endpoints/list          (목록)
#             /api/3.0/mlflow/gateway/endpoints/{name}        (상세)
#         (브라우저 UI 는 ajax-api 를 쓰지만 프로그램 접근은 api 가 표준.
#          환경에 따라 ajax-api 만 열려 있을 수 있어 두 경로를 폴백한다.)
#
#  [인증] 이 조회는 MLflow 로그인 권한이 필요하다. judge_eval 에서 gateway 에
#         Basic 인증(base64(아이디:비번)) 헤더를 실어보낸 것과 동일하게,
#         Authorization: Basic <base64(USERNAME:PASSWORD)> 헤더를 붙인다.
# #############################################################################

def _gateway_headers():
    """MLflow 아이디/비번으로 Basic 인증 헤더를 만든다. (judge_eval 방식과 동일)

    Authorization: Basic base64(USERNAME:PASSWORD)
    """
    import base64
    user = MLFLOW_USERNAME if isinstance(MLFLOW_USERNAME, str) else ""
    pw = MLFLOW_PASSWORD if isinstance(MLFLOW_PASSWORD, str) else ""
    token = base64.b64encode(f"{user}:{pw}".encode("utf-8")).decode("utf-8")
    return {"Authorization": f"Basic {token}"}


def _gateway_get(path_suffix):
    """3.x gateway REST 경로를 Basic 인증 헤더로 호출한다.
    api / ajax-api 두 prefix 를 순서대로 시도(폴백)한다.
    반환: (json dict, 사용된 url)  /  실패 시 예외 raise.
    """
    import requests

    base = MLFLOW_TRACKING_URI.rstrip("/")
    headers = _gateway_headers()
    last_exc = None
    for prefix in ("api", "ajax-api"):
        url = f"{base}/{prefix}/3.0/mlflow/gateway/{path_suffix}"
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 200:
                return r.json(), url
            # 404 면 다음 prefix 시도, 그 외(401/403 등)는 바로 알린다.
            if r.status_code in (401, 403):
                raise PermissionError(
                    f"{r.status_code} 인증/권한 거부 (MLflow 아이디/비번 확인). url={url}"
                )
            last_exc = RuntimeError(f"HTTP {r.status_code} at {url} - {r.text[:200]}")
        except PermissionError:
            raise
        except Exception as e:
            last_exc = e
    # 두 경로 모두 실패
    raise last_exc if last_exc else RuntimeError("gateway 조회 실패 (원인 불명)")


def inspect_gateway(mlflow):
    _sep("1) Gateway 엔드포인트 조회")
    print("조회 중 ...", end=" ", flush=True)
    try:
        data, used_url = _gateway_get("endpoints/list")
        endpoints = data.get("endpoints", [])
        print(f"완료  (경로: {used_url})", flush=True)
    except Exception as e:
        print("실패", flush=True)
        _err("gateway 엔드포인트 목록 조회(endpoints/list)", e)
        return

    if not endpoints:
        print("  등록된 gateway 엔드포인트가 없습니다.")
        return

    def render(ep):
        # REST 응답은 dict. 이름/타입 키를 꺼낸다.
        name = ep.get("name", "?")
        etype = ep.get("endpoint_type") or ep.get("task") or "?"
        # 타입을 알아보기 쉽게 표시 (chat / embeddings / completions)
        tag = ""
        t = str(etype).lower()
        if "embedding" in t:
            tag = "  <- 임베딩 (RAG 조회용 가능)"
        elif "chat" in t:
            tag = "  <- chat (LLM/Judge 용)"
        elif "completion" in t:
            tag = "  <- completions"
        return f"{name:30s} [{etype}]{tag}"

    while True:
        print(f"\n  총 {len(endpoints)} 개 엔드포인트:")
        chosen = _pick(endpoints, render)
        if chosen is None:
            return
        _show_gateway_detail(chosen)


def _show_gateway_detail(ep):
    name = ep.get("name", "?")
    _sep(f"[Gateway 상세] {name}")

    # 상세 재조회 (endpoints/{name}). 실패하면 목록에서 받은 dict 를 그대로 사용.
    detail = ep
    try:
        data, _ = _gateway_get(f"endpoints/{name}")
        if isinstance(data, dict) and data:
            detail = data
    except Exception as e:
        _err(f"엔드포인트 상세 조회(endpoints/{name})", e)

    for key in ("name", "endpoint_type", "task", "endpoint_url", "limit"):
        if key in detail and detail[key] is not None:
            print(f"  {key:15s}: {detail[key]}")
    # model 안쪽(provider/name)까지
    model = detail.get("model")
    if isinstance(model, dict):
        for a in ("name", "provider"):
            if model.get(a) is not None:
                print(f"    model.{a:11s}: {model[a]}")


# #############################################################################
# 2) Prompt 조회
# #############################################################################

def inspect_prompt(mlflow):
    _sep("2) Prompt 조회")
    print("조회 중 ...", end=" ", flush=True)
    try:
        prompts = mlflow.genai.search_prompts()
        prompts = list(prompts)
        print("완료", flush=True)
    except Exception as e:
        print("실패", flush=True)
        _err("프롬프트 목록 조회(search_prompts)", e)
        return

    if not prompts:
        print("  등록된 프롬프트가 없습니다.")
        return

    def render(p):
        name = getattr(p, "name", "?")
        return f"{name}"

    while True:
        print(f"\n  총 {len(prompts)} 개 프롬프트:")
        chosen = _pick(prompts, render)
        if chosen is None:
            return
        _show_prompt_detail(chosen, mlflow)


def _show_prompt_detail(p, mlflow):
    name = getattr(p, "name", "?")
    _sep(f"[Prompt 상세] {name}")

    # 버전 목록 조회 (search_prompt_versions 는 Databricks 전용일 수 있음 → 순차 탐색 폴백)
    from mlflow import MlflowClient
    client = MlflowClient()
    versions = []
    try:
        vs = client.search_prompt_versions(name)
        versions = list(getattr(vs, "prompt_versions", vs) or [])
    except Exception:
        # 폴백: v1 부터 순차 load 시도
        v = 1
        while v <= 50:
            try:
                pv = mlflow.genai.load_prompt(name, version=v)
                versions.append(pv)
                v += 1
            except Exception:
                break

    if not versions:
        print("  버전 정보를 가져오지 못했습니다 (권한/버전 API 차이일 수 있음).")
        return

    print(f"  버전 {len(versions)} 개:")
    for pv in versions:
        ver = getattr(pv, "version", "?")
        template = getattr(pv, "template", "")
        # 변수 포함 여부 표시 ({{var}})
        has_var = "{{" in str(template)
        var_tag = "  (변수 포함 {{...}})" if has_var else ""
        preview = str(template).replace("\n", " ")[:60]
        print(f"    - v{ver}: {preview}...{var_tag}")


# #############################################################################
# 3) Judge / Scorer 조회
# #############################################################################

def inspect_judge(mlflow):
    _sep("3) Judge / Scorer 조회")
    print("조회 중 ...", end=" ", flush=True)
    try:
        kwargs = {}
        if EXPERIMENT_NAME:
            exp = mlflow.get_experiment_by_name(EXPERIMENT_NAME)
            if exp is not None:
                kwargs["experiment_id"] = exp.experiment_id
        scorers = mlflow.genai.list_scorers(**kwargs)
        scorers = list(scorers)
        print("완료", flush=True)
    except Exception as e:
        print("실패", flush=True)
        _err("judge/scorer 목록 조회(list_scorers)", e)
        print("  참고: 이 서버(OSS 버전)에서 scorer 조회를 지원하지 않을 수 있습니다.")
        return

    if not scorers:
        print("  등록된 judge/scorer 가 없습니다.")
        return

    def render(s):
        name = getattr(s, "name", "?")
        return f"{name}"

    while True:
        print(f"\n  총 {len(scorers)} 개 judge/scorer:")
        chosen = _pick(scorers, render)
        if chosen is None:
            return
        _show_judge_detail(chosen)


def _show_judge_detail(s):
    name = getattr(s, "name", "?")
    _sep(f"[Judge/Scorer 상세] {name}")
    for attr in ("name", "model", "guidelines", "instructions", "aggregations"):
        val = getattr(s, attr, None)
        if val is not None:
            print(f"  {attr:12s}: {str(val)[:300]}")
    # 자동평가 스케줄 정보 (있으면)
    sched = getattr(s, "sample_rate", None) or getattr(s, "schedule", None)
    if sched is not None:
        print(f"  자동평가     : {sched}")


# #############################################################################
# 메인 메뉴
# #############################################################################

def main():
    mlflow = _setup()
    menu = {
        "1": ("Gateway 엔드포인트 조회", inspect_gateway),
        "2": ("Prompt 조회",           inspect_prompt),
        "3": ("Judge / Scorer 조회",   inspect_judge),
    }
    while True:
        _sep("MLflow 조회 헬퍼")
        for k, (label, _) in menu.items():
            print(f"  [{k}] {label}")
        print("  [0] 종료")
        sel = input("조회할 대상 선택: ").strip()
        if sel == "0":
            print("종료합니다.")
            return
        if sel in menu:
            try:
                menu[sel][1](mlflow)
            except KeyboardInterrupt:
                print("\n(취소)")
            except Exception as e:
                _err(f"'{menu[sel][0]}' 실행 중", e)
        else:
            print("올바른 번호를 입력하세요.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n종료합니다.")
