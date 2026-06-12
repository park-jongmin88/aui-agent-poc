# =============================================================
#  AIU DeepAgent - 진입점 (CLI)
#  AI STUDIO - ML/DL 프로세스 자동화
# =============================================================
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
VERSION = "0.1.0 (POC)"

# 필수 .env 키 정의
REQUIRED_ENV_KEYS = [
    "LLM_BASE_URL",      # 사내 LLM 공급자 URL
    "LLM_API_KEY",       # 사내 LLM API KEY
    "LLM_MODEL_NAME",    # 사용할 모델명
    "MLFLOW_TRACKING_URI",
]


# -------------------------------------------------------------
#  시작 시퀀스 - 체크 단계
# -------------------------------------------------------------
def _banner():
    print("=" * 52)
    print(f"   AIU DeepAgent  v{VERSION}")
    print("   AI STUDIO - ML/DL 프로세스 자동화 CLI")
    print("=" * 52)
    print()


def check_env() -> bool:
    """[1/4] .env 필수 키 확인. 누락 시 안내 후 종료."""
    load_dotenv(BASE_DIR / ".env")
    missing = [k for k in REQUIRED_ENV_KEYS if not os.getenv(k)]
    if missing:
        print("  [1/4] .env 설정 확인        ✗")
        print(f"        누락된 키: {', '.join(missing)}")
        print("        .env.example 을 복사해 .env 를 작성하세요.")
        return False
    # 사내 넥서스: 스킬이 띄우는 하위 프로세스의 pip도 넥서스를 보도록 반영
    if os.getenv("PIP_INDEX_URL"):
        os.environ["PIP_INDEX_URL"] = os.getenv("PIP_INDEX_URL")
    print("  [1/4] .env 설정 확인        ✓")
    return True


def check_llm():
    """[2/4] 사내 LLM 연결 확인. 실패해도 경고 후 진행."""
    try:
        from langchain_openai import ChatOpenAI

        model = ChatOpenAI(
            base_url=os.getenv("LLM_BASE_URL"),
            api_key=os.getenv("LLM_API_KEY"),
            model=os.getenv("LLM_MODEL_NAME"),
            timeout=10,
        )
        model.invoke("ping")  # 간단한 연결 확인 1회
        print("  [2/4] 사내 LLM 연결 확인    ✓")
    except Exception as e:
        print("  [2/4] 사내 LLM 연결 확인    ! (경고)")
        print(f"        {type(e).__name__}: {e}")
        print("        LLM 호출 시점에 다시 시도합니다.")


def check_mlflow():
    """[3/4] MLflow 연결 확인. 실패해도 경고 후 진행 (로컬 스킬은 사용 가능)."""
    try:
        import mlflow

        mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI"))
        # 인증 정보가 .env에 있으면 환경변수로 노출
        if os.getenv("MLFLOW_TRACKING_USERNAME"):
            os.environ["MLFLOW_TRACKING_USERNAME"] = os.getenv("MLFLOW_TRACKING_USERNAME")
        if os.getenv("MLFLOW_TRACKING_PASSWORD"):
            os.environ["MLFLOW_TRACKING_PASSWORD"] = os.getenv("MLFLOW_TRACKING_PASSWORD")
        mlflow.search_experiments(max_results=1)  # 접속 체크
        print("  [3/4] MLflow 연결 확인      ✓")
    except Exception as e:
        print("  [3/4] MLflow 연결 확인      ! (경고)")
        print(f"        {type(e).__name__}: {e}")
        print("        init / validate 등 로컬 스킬은 사용 가능합니다.")


def load_agent():
    """[4/4] 스킬 로딩 및 DeepAgent 생성."""
    from langchain_openai import ChatOpenAI
    from deepagents import create_deep_agent
    from deepagents.backends.filesystem import FilesystemBackend

    model = ChatOpenAI(
        base_url=os.getenv("LLM_BASE_URL"),
        api_key=os.getenv("LLM_API_KEY"),
        model=os.getenv("LLM_MODEL_NAME"),
    )

    agent_md = BASE_DIR / "agent.md"
    system_prompt = agent_md.read_text(encoding="utf-8") if agent_md.exists() else None

    agent = create_deep_agent(
        model=model,
        backend=FilesystemBackend(root_dir=str(BASE_DIR), virtual_mode=False),
        skills=["skills/"],           # 루트의 보이는 skills 폴더 (backend root 기준 상대경로)
        system_prompt=system_prompt,
    )

    names = _skill_names()
    print(f"  [4/4] 스킬 로딩             ✓  {len(names)}개 ({', '.join(names)})")
    return agent


def _skill_names():
    skills_dir = BASE_DIR / "skills"
    return sorted(
        p.name for p in skills_dir.iterdir()
        if p.is_dir() and (p / "SKILL.md").exists()
    ) if skills_dir.exists() else []


# -------------------------------------------------------------
#  슬래시 명령어
# -------------------------------------------------------------
def _cmd_help():
    print("""
  /help     명령어 목록
  /skills   로드된 스킬 목록
  /env      현재 설정 (키는 마스킹)
  /model    model/ 하위 폴더 목록
  /clear    대화 히스토리 초기화
  /exit     종료
""")


def _cmd_skills():
    for name in _skill_names():
        desc = ""
        skill_md = BASE_DIR / "skills" / name / "SKILL.md"
        for line in skill_md.read_text(encoding="utf-8").splitlines():
            if line.startswith("description:"):
                desc = line.split(":", 1)[1].strip()
                break
        print(f"  - {name:<10} {desc}")


def _mask(v: str) -> str:
    if not v:
        return "(없음)"
    return v[:4] + "*" * max(len(v) - 4, 0) if len(v) > 4 else "****"


def _cmd_env():
    print(f"  LLM_BASE_URL        = {os.getenv('LLM_BASE_URL')}")
    print(f"  LLM_API_KEY         = {_mask(os.getenv('LLM_API_KEY', ''))}")
    print(f"  LLM_MODEL_NAME      = {os.getenv('LLM_MODEL_NAME')}")
    print(f"  MLFLOW_TRACKING_URI = {os.getenv('MLFLOW_TRACKING_URI')}")


def _cmd_model():
    model_dir = BASE_DIR / "model"
    if not model_dir.exists():
        print("  model/ 폴더가 없습니다.")
        return
    for d in sorted(model_dir.iterdir()):
        if d.is_dir():
            has_run = "run.py ✓" if (d / "run.py").exists() else "run.py 없음"
            print(f"  - model/{d.name:<22} {has_run}")
    print("  (작업 대상은 대화에서 폴더명으로 지정하세요. 예: 'sklearn_sample 학습해줘')")


# -------------------------------------------------------------
#  대화 루프
# -------------------------------------------------------------
def chat_loop(agent):
    print()
    print("  준비 완료. 명령을 입력하세요. (/help 로 도움말)")
    print("-" * 52)

    history = []  # 멀티턴 히스토리

    while True:
        try:
            user_input = input("aiu> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n  종료합니다.")
            break

        if not user_input:
            continue

        # 슬래시 명령 처리
        if user_input.startswith("/"):
            cmd = user_input.lower()
            if cmd == "/exit":
                print("  종료합니다.")
                break
            elif cmd == "/help":
                _cmd_help()
            elif cmd == "/skills":
                _cmd_skills()
            elif cmd == "/env":
                _cmd_env()
            elif cmd == "/model":
                _cmd_model()
            elif cmd == "/clear":
                history = []
                print("  대화 히스토리를 초기화했습니다.")
            else:
                print("  알 수 없는 명령입니다. /help 를 입력하세요.")
            continue

        # 에이전트 호출
        history.append({"role": "user", "content": user_input})
        try:
            t0 = time.time()
            result = agent.invoke({"messages": history})
            messages = result["messages"]
            answer = messages[-1].content
            # 히스토리를 에이전트 결과로 갱신 (툴 호출 포함 전체 맥락 유지)
            history = messages
            print()
            print(answer)
            print(f"\n  ({time.time() - t0:.1f}s)")
            print("-" * 52)
        except Exception as e:
            print(f"  [오류] {type(e).__name__}: {e}")
            history.pop()  # 실패한 입력 제거


def main():
    _banner()
    if not check_env():
        sys.exit(1)
    check_llm()
    check_mlflow()
    agent = load_agent()
    chat_loop(agent)


if __name__ == "__main__":
    main()
