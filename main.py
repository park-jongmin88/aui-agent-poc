# =============================================================
#  aiu-agent - 진입점 (CLI)  [DeepAgents 기반]
#  AI STUDIO - ML/DL 프로세스 자동화
#
#  실행 모드:
#    python main.py            체크 후 CLI 진입
#    python main.py --setup    의존성 설치 + 체크 + CLI 진입 (quickstart용)
#    python main.py --check    체크만 수행하고 종료
# =============================================================
import os
import sys
import time
import subprocess
from pathlib import Path

import yaml

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.yaml"
VERSION = "0.2.0 (POC)"

SAMPLE_CONFIG = """\
# =====================================================
#  aiu-agent 설정
#  TODO 표시된 값을 환경에 맞게 수정하세요.
#  수정 후 CLI에서 /reload 로 즉시 반영할 수 있습니다.
# =====================================================
llm:
  default: my-llm                # 시작 시 사용할 provider의 name
  providers:
    - name: my-llm
      base_url: http://your-llm-server:8000/v1   # TODO: 사내 LLM 주소 (OpenAI 호환)
      api_key: your-api-key                      # TODO: API 키
      model: your-model-name                     # TODO: 모델명
    # 추가 LLM은 아래 형식으로 계속 등록 (CLI의 /llm 으로 전환)
    # - name: backup-llm
    #   base_url: http://...
    #   api_key: ...
    #   model: ...

pip:
  index_url: ""                  # TODO: 사내 넥서스 주소 (비우면 기본 pip 설정)
"""

PLACEHOLDER_TOKENS = ("your-", "http://your-")


# -------------------------------------------------------------
#  config.yaml 로딩 / 생성 / 마법사
# -------------------------------------------------------------
def load_config(create_if_missing: bool = True) -> dict:
    if not CONFIG_PATH.exists():
        if not create_if_missing:
            return {}
        CONFIG_PATH.write_text(SAMPLE_CONFIG, encoding="utf-8")
        print(f"        config.yaml 이 없어 새로 생성했습니다 → {CONFIG_PATH}")
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_providers(cfg: dict) -> list:
    return (cfg.get("llm") or {}).get("providers") or []


def get_default_provider(cfg: dict):
    providers = get_providers(cfg)
    if not providers:
        return None
    default_name = (cfg.get("llm") or {}).get("default")
    for p in providers:
        if p.get("name") == default_name:
            return p
    return providers[0]


def is_placeholder(provider: dict) -> bool:
    if not provider:
        return True
    for key in ("base_url", "api_key", "model"):
        v = str(provider.get(key) or "")
        if not v or any(tok in v for tok in PLACEHOLDER_TOKENS):
            return True
    return False


def apply_pip_index(cfg: dict):
    """우선순위: OS 환경변수 > config.yaml"""
    if os.environ.get("PIP_INDEX_URL"):
        return
    url = ((cfg.get("pip") or {}).get("index_url") or "").strip()
    if url and not any(tok in url for tok in PLACEHOLDER_TOKENS):
        os.environ["PIP_INDEX_URL"] = url


def run_wizard(cfg: dict) -> dict:
    """대화형으로 첫 LLM provider를 입력받아 config.yaml 저장.
    입력 후 리뷰 화면에서 항목별 재입력이 가능하다."""
    try:
        from rich.console import Console
        from rich.panel import Panel
        console = Console()
    except ImportError:
        console = None

    def say(msg, style=None):
        if console:
            console.print(msg, style=style)
        else:
            print(msg)

    print()
    if console:
        console.print(Panel(
            "[bold]LLM 설정 정보를 입력해주세요.[/bold]\n"
            "모르는 항목은 [cyan]Enter[/cyan]로 비워두고, 나중에\n"
            f"[cyan]{CONFIG_PATH}[/cyan] 파일을 직접 열어 수정해도 됩니다.\n"
            "[grey50](붙여넣기: Ctrl+V 또는 Shift+Insert / 마우스 우클릭)[/grey50]",
            title="[2/4] 처음 실행 - 초기 설정", border_style="cyan",
        ))
    else:
        print("  [2/4] 처음 실행입니다 - LLM 설정 정보를 입력해주세요.")
        print(f"        모르는 항목은 Enter로 비워두고, 나중에 {CONFIG_PATH} 를 직접 수정해도 됩니다.")
        print("        (붙여넣기: Ctrl+V 또는 Shift+Insert / 마우스 우클릭)")
    print()

    fields = [
        ("name", "이름(별칭)        "),
        ("base_url", "주소(base_url)   "),
        ("api_key", "API 키           "),
        ("model", "모델명           "),
    ]
    values = {"name": "", "base_url": "", "api_key": "", "model": ""}

    def ask(key, label):
        suffix = " [my-llm]" if key == "name" else ""
        values[key] = input(f"  {label}{suffix} : ").strip()

    for key, label in fields:
        ask(key, label)

    # ----- 리뷰 & 수정 루프 -----
    while True:
        print()
        say("  --- 입력 확인 ---", style="bold")
        for i, (key, label) in enumerate(fields, 1):
            shown = values[key]
            if key == "api_key" and shown:
                shown = _mask(shown)
            shown = shown or "(미입력)"
            print(f"   {i}) {label}: {shown}")
        print()
        sel = input("  수정할 번호 (Enter=완료): ").strip()
        if not sel:
            break
        if sel.isdigit() and 1 <= int(sel) <= len(fields):
            key, label = fields[int(sel) - 1]
            ask(key, label)
        else:
            say("  1~4 사이의 번호를 입력하세요.", style="yellow")

    name = values["name"] or "my-llm"
    provider = {
        "name": name,
        "base_url": values["base_url"] or "http://your-llm-server:8000/v1",
        "api_key": values["api_key"] or "your-api-key",
        "model": values["model"] or "your-model-name",
    }
    cfg.setdefault("llm", {})
    cfg["llm"]["default"] = name
    providers = get_providers(cfg)
    # 같은 이름이 있으면 교체, 없으면 맨 앞에 추가
    providers = [p for p in providers if p.get("name") != name]
    providers.insert(0, provider)
    cfg["llm"]["providers"] = providers

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)

    print()
    if is_placeholder(provider):
        say(f"  ⚠ 비워둔 항목이 있습니다. [yellow]{CONFIG_PATH}[/yellow] 를 열어 "
            f"TODO 값을 채운 뒤 다시 실행해주세요.", style="yellow")
    else:
        say(f"  ✓ 저장 완료 → {CONFIG_PATH}", style="green")
    say(f"  (추가 LLM 등록·수정은 {CONFIG_PATH} 직접 편집 후 CLI에서 /reload)")
    print()
    return cfg


# -------------------------------------------------------------
#  --setup : 의존성 설치 (rich Live로 로그가 흘렀다 사라지는 표시)
# -------------------------------------------------------------
def install_dependencies() -> bool:
    req = BASE_DIR / "setting" / "requirements.txt"
    cmd = [sys.executable, "-m", "pip", "install", "-r", str(req)]
    if os.environ.get("PIP_INDEX_URL"):
        cmd += ["--index-url", os.environ["PIP_INDEX_URL"]]

    try:
        from rich.live import Live
        from rich.panel import Panel
        from rich.console import Console

        console = Console()
        console.print("  [3/4] 의존성 설치 중...")
        N = 3  # 표시할 줄 수 (고정)
        tail: list[str] = [""] * N
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", bufsize=1,
        )
        with Live(console=console, refresh_per_second=8, transient=True) as live:
            live.update(Panel("\n".join(tail), border_style="grey50", height=N + 2))
            for line in proc.stdout:
                line = line.rstrip()
                if not line:
                    continue
                tail.append(line[:90])
                tail = tail[-N:]
                live.update(Panel("\n".join(tail), border_style="grey50", height=N + 2))
        proc.wait()
        ok = proc.returncode == 0
        console.print(f"  [3/4] 의존성 설치             {'✓' if ok else '✗ 실패 (로그 확인 필요)'}")
        return ok
    except ImportError:
        # rich가 없으면 일반 출력으로 폴백
        print("  [3/4] 의존성 설치 중... (수 분 소요)")
        ret = subprocess.run(cmd).returncode
        ok = ret == 0
        print(f"  [3/4] 의존성 설치             {'✓' if ok else '✗ 실패'}")
        return ok


# -------------------------------------------------------------
#  --setup : 실행 스크립트 생성
# -------------------------------------------------------------
def generate_run_scripts():
    """aiu-agent-run.bat / .sh 생성 (이후 quickstart 없이 바로 실행).
    bat 자체에 echo 블록을 두면 콘솔 stdin이 오염될 수 있어 여기서 생성한다."""
    venv_py_win = r".venv\Scripts\python.exe"
    bat = (
        "@echo off\r\n"
        "title aiu-agent\r\n"
        f'"%~dp0{venv_py_win}" "%%~dp0main.py" %%*\r\n'
    ).replace("%%~dp0main.py", "%~dp0main.py")
    (BASE_DIR / "aiu-agent-run.bat").write_bytes(bat.encode("cp949"))

    sh = (
        "#!/usr/bin/env bash\n"
        'DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"\n'
        '"$DIR/.venv/bin/python" "$DIR/main.py" "$@"\n'
    )
    sh_path = BASE_DIR / "aiu-agent-run.sh"
    sh_path.write_text(sh, encoding="utf-8")
    try:
        os.chmod(sh_path, 0o755)
    except OSError:
        pass


# -------------------------------------------------------------
def _banner():
    try:
        from rich.console import Console
        c = Console()
        c.print("=" * 52, style="grey50")
        c.print(f"   aiu-agent  v{VERSION}", style="bold cyan")
        c.print("   AI STUDIO - ML/DL 프로세스 자동화 CLI", style="grey50")
        c.print("=" * 52, style="grey50")
    except ImportError:
        print("=" * 52)
        print(f"   aiu-agent  v{VERSION}")
        print("   AI STUDIO - ML/DL 프로세스 자동화 CLI")
        print("=" * 52)
    print()


# -------------------------------------------------------------
#  엔트리
# -------------------------------------------------------------
def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    _banner()

    # [1/4] Python/가상환경 (여기 도달했으면 통과)
    print("  [1/4] Python / 가상환경       ✓")

    # [2/4] 설정 (config.yaml) - 의존성 설치 전에 먼저 확인/입력
    cfg = check_config(interactive=(mode != "--check"))
    if cfg is None:
        sys.exit(1)
    apply_pip_index(cfg)

    # [3/4] 의존성 설치 (setup 모드에서만 실제 설치)
    if mode == "--setup":
        if not install_dependencies():
            sys.exit(1)
        generate_run_scripts()
    else:
        print("  [3/4] 의존성                  ✓ (--setup 으로 재설치 가능)")

    # [4/4] 필수 체크 목록 - 하나라도 실패하면 차단
    #       향후 항목 추가 시 이 리스트에 (이름, 함수) 형태로 추가
    checks = [
        ("llm", lambda: check_llm(cfg, interactive=(mode != "--check"))),
    ]
    results = {}
    for key, fn in checks:
        r = fn()
        if r is None:
            sys.exit(1)
        results[key] = r
    provider = results["llm"]

    if mode == "--check":
        print("\n  체크 완료. (--check 모드 종료)")
        return

    # 스킬 로딩 + CLI 진입
    agent = load_agent(provider)
    chat_loop(cfg, provider, agent)


def check_config(interactive: bool = True):
    """[2/4] config.yaml 확인. placeholder면 마법사 진행 또는 안내."""
    cfg = load_config()
    apply_pip_index(cfg)
    provider = get_default_provider(cfg)

    if not is_placeholder(provider):
        print("  [2/4] 설정(config.yaml)       ✓")
        return cfg

    if not interactive:
        print("  [2/4] 설정(config.yaml)       ✗ 아직 설정되지 않았습니다.")
        print(f"        {CONFIG_PATH} 의 TODO 항목을 채운 뒤 다시 실행해주세요.")
        return None

    cfg = run_wizard(cfg)
    if not is_placeholder(get_default_provider(cfg)):
        print("  [2/4] 설정(config.yaml)       ✓")
        return cfg
    return None


def _build_chat_model(provider: dict, timeout: int | None = None):
    from langchain_openai import ChatOpenAI
    kwargs = dict(
        base_url=provider["base_url"],
        api_key=provider["api_key"],
        model=provider["model"],
    )
    if timeout:
        kwargs["timeout"] = timeout
    return ChatOpenAI(**kwargs)


def check_llm(cfg: dict, interactive: bool = True):
    """[4/4] 필수 체크 - LLM 연결. 실패 시 진행 차단 (다른 provider 선택 가능).
    향후 다른 필수 체크가 추가되면 이 함수처럼 (성공/None) 패턴으로 추가하고
    main()의 체크 목록에 등록한다."""
    providers = get_providers(cfg)
    provider = get_default_provider(cfg)

    while True:
        try:
            _build_chat_model(provider, timeout=15).invoke("ping")
            print(f"  [4/4] LLM 연결 ({provider['name']})        ✓")
            return provider
        except Exception as e:
            print(f"  [4/4] LLM 연결 ({provider['name']})        ✗")
            print(f"        {type(e).__name__}: {str(e)[:120]}")

        # 실패 처리: 다른 provider가 있으면 선택, 없으면 차단 종료
        usable = [p for p in providers if not is_placeholder(p)]
        if interactive and len(usable) > 1:
            print("\n  등록된 다른 LLM:")
            for i, p in enumerate(usable, 1):
                print(f"    {i}. {p['name']}  ({p['model']})")
            sel = input("  번호 선택 (Enter=중단): ").strip()
            if sel.isdigit() and 1 <= int(sel) <= len(usable):
                provider = usable[int(sel) - 1]
                continue
        print("\n  LLM 연결이 되어야 진행할 수 있습니다.")
        print(f"  {CONFIG_PATH} 의 LLM 정보를 확인한 뒤 다시 실행해주세요.")
        return None


def load_agent(provider: dict):
    """스킬 로딩 및 DeepAgent 생성."""
    from deepagents import create_deep_agent
    from deepagents.backends.filesystem import FilesystemBackend

    agent_md = BASE_DIR / "agent.md"
    system_prompt = agent_md.read_text(encoding="utf-8") if agent_md.exists() else None

    agent = create_deep_agent(
        model=_build_chat_model(provider),
        backend=FilesystemBackend(root_dir=str(BASE_DIR), virtual_mode=False),
        skills=["skills/"],           # 루트의 보이는 skills 폴더
        system_prompt=system_prompt,
    )
    names = _skill_names()
    print(f"  스킬 로딩                     ✓  {len(names)}개 ({', '.join(names)})")
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
  /config   현재 설정 (키는 마스킹)
  /model    model/ 하위 폴더 목록
  /llm      등록된 LLM 목록 + 전환
  /reload   config.yaml 재로드 + 에이전트 재구성
  /clear    대화 히스토리 초기화
  /exit     종료
""")


def _cmd_skills():
    for name in _skill_names():
        desc = ""
        skill_md = BASE_DIR / "skills" / name / "SKILL.md"
        for line in skill_md.read_text(encoding="utf-8").splitlines():
            if line.startswith("description:"):
                desc = line.split(":", 1)[1].strip().strip('"')
                break
        print(f"  - {name:<10} {desc[:60]}")


def _mask(v: str) -> str:
    if not v:
        return "(없음)"
    return v[:4] + "*" * max(len(v) - 4, 0) if len(v) > 4 else "****"


def _cmd_config(cfg: dict, current: dict):
    print(f"  config: {CONFIG_PATH}")
    print(f"  사용 중 LLM: {current['name']}")
    for p in get_providers(cfg):
        mark = " ← 사용 중" if p.get("name") == current.get("name") else ""
        flag = " (미설정)" if is_placeholder(p) else ""
        print(f"    - {p.get('name')}: {p.get('model')} @ {p.get('base_url')} "
              f"key={_mask(str(p.get('api_key') or ''))}{flag}{mark}")
    print(f"  PIP_INDEX_URL = {os.environ.get('PIP_INDEX_URL', '(기본)')}")


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


def _cmd_llm(cfg: dict, current: dict):
    """등록 LLM 목록 표시 + 번호 선택으로 전환. 전환 시 (provider) 반환."""
    usable = [p for p in get_providers(cfg) if not is_placeholder(p)]
    if not usable:
        print("  사용 가능한 LLM이 없습니다. config.yaml 을 확인하세요.")
        return None
    for i, p in enumerate(usable, 1):
        mark = " ← 사용 중" if p["name"] == current["name"] else ""
        print(f"  {i}. {p['name']}  ({p['model']} @ {p['base_url']}){mark}")
    sel = input("  전환할 번호 (Enter=유지): ").strip()
    if sel.isdigit() and 1 <= int(sel) <= len(usable):
        chosen = usable[int(sel) - 1]
        if chosen["name"] != current["name"]:
            return chosen
    return None


# -------------------------------------------------------------
#  대화 루프
# -------------------------------------------------------------
def chat_loop(cfg: dict, provider: dict, agent):
    print()
    print("  준비 완료. 명령을 입력하세요. (/help 로 도움말)")
    print("-" * 52)

    history = []

    while True:
        try:
            user_input = input("aiu> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n  종료합니다.")
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            cmd = user_input.lower()
            if cmd == "/exit":
                print("  종료합니다.")
                break
            elif cmd == "/help":
                _cmd_help()
            elif cmd == "/skills":
                _cmd_skills()
            elif cmd == "/config":
                _cmd_config(cfg, provider)
            elif cmd == "/model":
                _cmd_model()
            elif cmd == "/llm":
                chosen = _cmd_llm(cfg, provider)
                if chosen:
                    try:
                        print(f"  {chosen['name']} 연결 확인 중...")
                        _build_chat_model(chosen, timeout=15).invoke("ping")
                        provider = chosen
                        agent = load_agent(provider)
                        print(f"  전환 완료 → {provider['name']}")
                    except Exception as e:
                        print(f"  전환 실패: {type(e).__name__}: {str(e)[:100]}")
            elif cmd == "/reload":
                cfg = load_config()
                apply_pip_index(cfg)
                new_p = get_default_provider(cfg)
                # 현재 사용 중인 이름이 여전히 있으면 그것을 유지
                for p in get_providers(cfg):
                    if p.get("name") == provider.get("name"):
                        new_p = p
                        break
                try:
                    _build_chat_model(new_p, timeout=15).invoke("ping")
                    provider = new_p
                    agent = load_agent(provider)
                    print(f"  재로드 완료 (LLM: {provider['name']})")
                except Exception as e:
                    print(f"  재로드 했지만 LLM 연결 실패: {str(e)[:100]}")
                    print("  config.yaml 을 확인하세요. (기존 세션은 유지됩니다)")
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
            history = messages
            print()
            print(answer)
            print(f"\n  ({time.time() - t0:.1f}s)")
            print("-" * 52)
        except Exception as e:
            print(f"  [오류] {type(e).__name__}: {e}")
            history.pop()


if __name__ == "__main__":
    main()
