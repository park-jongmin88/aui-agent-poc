# =============================================================
#  aiu-agent - 진입점 (CLI)  [DeepAgents 기반]
#  AI STUDIO - 자동화 어시스턴트
#
#  실행 모드:
#    python main.py            체크 후 CLI 진입
#    python main.py --setup    의존성 설치 + 체크 + CLI 진입 (install.bat/sh 용)
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
  active: my-llm

  providers:
    # ── 사용할 LLM (필수) ──────────────────────────
    - name: my-llm
      type: openai
      base_url: http://your-llm-server:8000/v1   # TODO
      api_key: your-api-key                      # TODO
      model: your-model-name                     # TODO

    # ── 참고 샘플 (주석 해제 후 사용) ───────────────

    # groq
    # - name: groq
    #   type: openai
    #   base_url: https://api.groq.com/openai/v1
    #   api_key: gsk_...
    #   model: llama-3.3-70b-versatile

    # Anthropic Claude (base_url 불필요)
    # - name: claude
    #   type: anthropic
    #   api_key: sk-ant-...
    #   model: claude-sonnet-4-6

    # Anthropic 호환 커스텀 엔드포인트 (사내 등)
    # - name: claude-custom
    #   type: anthropic
    #   base_url: https://your-anthropic-proxy.io
    #   api_key: sk-...
    #   model: claude-sonnet-4-6

    # OpenAI 공식
    # - name: openai
    #   type: openai
    #   base_url: https://api.openai.com/v1
    #   api_key: sk-...
    #   model: gpt-4o

    # Ollama (로컬)
    # - name: ollama
    #   type: openai
    #   base_url: http://localhost:11434/v1
    #   api_key: ollama
    #   model: llama3.2
"""

PLACEHOLDER_TOKENS = ("your-", "http://your-")


def _flush_stdin():
    """터미널에 남아있던 처리되지 않은 입력을 비운다.
    (이전 작업의 명령줄이 다음 input()에 끼어드는 것을 방지)"""
    try:
        if os.name == "nt":
            import msvcrt
            while msvcrt.kbhit():
                msvcrt.getch()
        else:
            import termios
            termios.tcflush(sys.stdin.fileno(), termios.TCIFLUSH)
    except Exception:
        pass


def _looks_like_path(s: str) -> bool:
    """base_url 등에 경로가 잘못 들어온 경우를 감지."""
    if not s:
        return False
    s_low = s.lower()
    if "\\" in s:
        return True
    if s_low.startswith(("c:", "/home/", "/root/", "/users/")):
        return True
    if s_low.startswith(("http://", "https://")):
        return False
    return False


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
    default_name = (cfg.get("llm") or {}).get("active")
    for p in providers:
        if p.get("name") == default_name:
            return p
    return providers[0]


def is_placeholder(provider: dict) -> bool:
    if not provider:
        return True
    ptype = (provider.get("type") or "openai").lower()
    check_keys = ["api_key", "model"]
    if ptype == "openai":
        check_keys.append("base_url")
    for key in check_keys:
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

    _flush_stdin()

    fields = [
        ("name",     "이름(별칭)        "),
        ("base_url", "주소(base_url)   "),
        ("api_key",  "API 키           "),
        ("model",    "모델명           "),
    ]
    values = {k: "" for k, _ in fields}
    ptype = "openai"  # 마법사는 openai 고정 (그 외는 config.yaml 직접 편집)

    def fetch_models(base_url: str, api_key: str) -> list[str]:
        """OpenAI 호환 /v1/models 엔드포인트로 모델 목록 조회."""
        try:
            import urllib.request, json as _json
            url = base_url.rstrip("/") + "/models"
            req = urllib.request.Request(
                url,
                headers={"Authorization": f"Bearer {api_key}",
                         "Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = _json.loads(resp.read())
            models = [m["id"] for m in data.get("data", [])]
            return sorted(models)
        except Exception:
            return []

    def ask(key, label):
        suffix = " [my-llm]" if key == "name" else ""
        while True:
            hint = " (Enter=목록 조회)" if key == "model" else ""
            v = input(f"  {label}{suffix}{hint} : ").strip()

            # base_url 경로 감지
            if key == "base_url" and _looks_like_path(v):
                say("  ⚠ URL 형식이 아닌 것 같습니다 (경로처럼 보입니다). 다시 입력해주세요.",
                    style="yellow")
                continue

            # model: Enter 시 목록 조회 (base_url/api_key 있을 때만)
            if key == "model" and not v:
                base = values.get("base_url", "").strip()
                akey = values.get("api_key", "").strip()
                if base and akey:
                    say("  모델 목록 조회 중...", style="grey50")
                    models = fetch_models(base, akey)
                    if models:
                        for i, m in enumerate(models, 1):
                            print(f"    {i}) {m}")
                        print()
                        sel = input("  번호 선택 (또는 직접 입력, Enter=나중에 설정): ").strip()
                        if sel.isdigit() and 1 <= int(sel) <= len(models):
                            values[key] = models[int(sel) - 1]
                            say(f"  → {values[key]}", style="cyan")
                            break
                        elif sel:
                            values[key] = sel
                            break
                        else:
                            values[key] = ""
                            break
                    else:
                        say("  ⚠ 목록 조회 실패. 직접 입력해주세요. (base_url/api_key 확인)", style="yellow")
                        continue
                else:
                    # base_url/api_key 없으면 경고 한 번만 보여주고 직접 입력으로
                    say("  (base_url/api_key가 없어 목록 조회 불가 — 직접 입력하거나 Enter로 건너뛰세요)", style="grey50")
                    v2 = input(f"  {label} : ").strip()
                    values[key] = v2
                    break

            values[key] = v
            break

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
            say(f"  1~{len(fields)} 사이의 번호를 입력하세요.", style="yellow")

    name = values["name"] or "my-llm"
    provider = {"name": name, "type": ptype}
    if ptype == "openai":
        provider["base_url"] = values.get("base_url") or "http://your-llm-server:8000/v1"
    provider["api_key"] = values.get("api_key") or "your-api-key"
    provider["model"]   = values.get("model")   or "your-model-name"
    cfg.setdefault("llm", {})
    cfg["llm"]["active"] = name
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
    """start.bat / start.sh 생성 (이후 install 없이 바로 실행).
    bat 자체에 echo 블록을 두면 콘솔 stdin이 오염될 수 있어 여기서 생성한다."""
    venv_py_win = r".venv\Scripts\python.exe"
    bat = (
        "@echo off\r\n"
        "title aiu-agent\r\n"
        f'"%~dp0{venv_py_win}" "%~dp0main.py" %*\r\n'
    )
    (BASE_DIR / "start.bat").write_bytes(bat.encode("cp949"))

    sh = (
        "#!/usr/bin/env bash\n"
        'DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"\n'
        '"$DIR/.venv/bin/python" "$DIR/main.py" "$@"\n'
    )
    sh_path = BASE_DIR / "start.sh"
    sh_path.write_text(sh, encoding="utf-8")
    try:
        os.chmod(sh_path, 0o755)
    except OSError:
        pass


def show_welcome(provider: dict):
    """체크 통과 후 화면을 정리하고 환영 화면을 표시한다."""
    # ANSI escape로 화면 클리어 (console.clear()보다 일부 터미널에서 안정적)
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()

    try:
        from rich.console import Console
        from rich.panel import Panel
        console = Console()
        console.print(Panel(
            "[bold cyan]🐳  aiu-agent[/bold cyan]\n"
            "[grey50]AI STUDIO 자동화 어시스턴트[/grey50]",
            border_style="cyan", width=46,
        ))
        print()
        console.print(f"  LLM: [cyan]{provider['name']}[/cyan] ({provider['model']})")
        print()
        console.print("  무엇이든 자연어로 요청하세요. 예시:")
        console.print('    [grey50]"작업 목록 보여줘"[/grey50]')
        console.print('    [grey50]"sklearn_sample 학습해줘"[/grey50]')
        print()
        console.print("  명령어 목록은 [cyan]/help[/cyan] 또는 [cyan]/?[/cyan] 입력")
    except ImportError:
        print("  🐳  aiu-agent")
        print("  AI STUDIO 자동화 어시스턴트")
        print()
        print(f"  LLM: {provider['name']} ({provider['model']})")
        print()
        print("  무엇이든 자연어로 요청하세요. 예시:")
        print('    "작업 목록 보여줘"')
        print('    "sklearn_sample 학습해줘"')
        print()
        print("  명령어 목록은 /help 또는 /? 입력")
    print()


# (cmd, desc, group) — group=True 이면 그룹 헤더 행
HELP_ITEMS = [
    ("/? /help", "도움말",          False),
    ("작업",     "",                True),
    ("/list",    "작업 목록",       False),
    ("/log",     "마지막 로그",     False),
    ("LLM",      "",                True),
    ("/llm",     "LLM 목록 + 전환", False),
    ("/reload",  "설정 재로드",     False),
    ("/config",  "현재 설정",       False),
    ("세션",     "",                True),
    ("/clear",   "대화 초기화",     False),
    ("/exit",    "종료",            False),
]


# -------------------------------------------------------------
#  에러 분류
# -------------------------------------------------------------
ERROR_GUIDES = [
    ("tool_use_failed", "LLM이 도구 호출 형식을 잘못 생성했습니다 (모델 호환성 문제).\n"
                         "    다른 LLM(예: GPT-4 계열)을 쓰면 줄어듭니다. /llm 으로 전환해보세요."),
    ("401", "API 키가 올바르지 않습니다. config.yaml 의 api_key 를 확인하세요."),
    ("authentication", "API 키가 올바르지 않습니다. config.yaml 의 api_key 를 확인하세요."),
    ("404", "모델을 찾을 수 없습니다. config.yaml 의 model 값을 확인하세요."),
    ("model_not_found", "모델을 찾을 수 없습니다. config.yaml 의 model 값을 확인하세요."),
    ("429", "요청 한도를 초과했습니다. 잠시 후 다시 시도하세요."),
    ("rate_limit", "요청 한도를 초과했습니다. 잠시 후 다시 시도하세요."),
    ("timeout", "LLM 서버에 연결할 수 없습니다. base_url 과 네트워크 상태를 확인하세요."),
    ("connection", "LLM 서버에 연결할 수 없습니다. base_url 과 네트워크 상태를 확인하세요."),
]


def classify_error(e: Exception) -> str:
    text = f"{type(e).__name__} {e}".lower()
    for keyword, guide in ERROR_GUIDES:
        if keyword in text:
            return guide
    return "예상치 못한 오류가 발생했습니다."


def show_error(e: Exception, last_log: dict):
    """한글 안내(info, yellow) + 에러 로그(error, red)를 응답과 동일한
    빈줄-라인-빈줄 규칙으로 표시. 전체 내용은 last_log에 저장."""
    guide = classify_error(e)
    short = f"{type(e).__name__}: {str(e)}"
    last_log["type"] = "error"
    last_log["text"] = short
    last_log["guide"] = guide

    SEP = "─" * 52
    try:
        from rich.console import Console
        from rich.panel import Panel
        console = Console()
        print()
        print(SEP)
        print()
        console.print(Panel(f"⚠️ {guide}", title="info", border_style="yellow", width=70))
        print()
        console.print(Panel(short[:300], title="error", border_style="red", width=70))
        print()
        console.print("  (전체 로그: /log)")
        print()
        print(SEP)
        print()
    except ImportError:
        print()
        print(SEP)
        print()
        print("  ┌─ info " + "─" * 41)
        print(f"  │ ⚠️ {guide}")
        print("  └" + "─" * 49)
        print()
        print("  ┌─ error " + "─" * 40)
        for line in short[:300].splitlines() or [short[:300]]:
            print(f"  │ {line}")
        print("  └" + "─" * 49)
        print()
        print("  (전체 로그: /log)")
        print()
        print(SEP)
        print()


def _cmd_log(last_log: dict):
    if not last_log:
        print("  표시할 로그가 없습니다.")
        return
    try:
        from rich.console import Console
        from rich.panel import Panel
        console = Console()
        body = last_log.get("text", "")
        if last_log.get("guide"):
            body = f"[안내] {last_log['guide']}\n\n{body}"
        console.print(Panel(body, title=f"log: {last_log.get('type', '')}",
                             border_style="grey50"))
    except ImportError:
        print(f"--- log: {last_log.get('type', '')} ---")
        if last_log.get("guide"):
            print(f"[안내] {last_log['guide']}\n")
        print(last_log.get("text", ""))


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

    # 스킬 로딩 + 환영화면 + CLI 진입
    agent = load_agent(provider)
    show_welcome(provider)
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
    ptype = (provider.get("type") or "openai").lower()

    if ptype == "anthropic":
        from langchain_anthropic import ChatAnthropic
        kwargs = dict(
            api_key=provider["api_key"],
            model=provider["model"],
        )
        if provider.get("base_url"):
            kwargs["base_url"] = provider["base_url"]
        if timeout:
            kwargs["timeout"] = timeout
        return ChatAnthropic(**kwargs)

    if ptype == "openai":
        from langchain_openai import ChatOpenAI
        kwargs = dict(
            base_url=provider["base_url"],
            api_key=provider["api_key"],
            model=provider["model"],
        )
        if timeout:
            kwargs["timeout"] = timeout
        return ChatOpenAI(**kwargs)

    raise ValueError(f"지원하지 않는 LLM type 입니다: '{ptype}' (openai | anthropic)")


def check_llm(cfg: dict, interactive: bool = True):
    """[4/4] 필수 체크 - LLM 연결. 실패 시 진행 차단 (다른 provider 선택 가능).
    향후 다른 필수 체크가 추가되면 이 함수처럼 (성공/None) 패턴으로 추가하고
    main()의 체크 목록에 등록한다."""
    providers = get_providers(cfg)
    provider = get_default_provider(cfg)

    while True:
        try:
            _build_chat_model(provider, timeout=15).invoke([{"role": "user", "content": "hi"}])
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
    try:
        from rich.console import Console
        from rich.table import Table
        from rich import box as rich_box
        console = Console()
        print()
        console.print("  할 수 있는 작업:", style="bold")
        console.print("    초기화(init)  검증(validate)  학습(train)  추론(predict)  배포(deploy)")
        print()
        tbl = Table(show_header=True, header_style="bold", box=rich_box.SIMPLE_HEAVY,
                    pad_edge=True, show_edge=True)
        tbl.add_column("명령어", style="", min_width=12)
        tbl.add_column("설명")
        for cmd, desc, is_group in HELP_ITEMS:
            if is_group:
                tbl.add_row(f"[bold cyan]{cmd}[/bold cyan]", "")
            else:
                tbl.add_row(cmd, desc)
        console.print(tbl)
        print()
    except ImportError:
        print()
        for cmd, desc, is_group in HELP_ITEMS:
            if is_group:
                print(f"  [{cmd}]")
            else:
                print(f"    {cmd:<12} {desc}")
        print()


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


def _cmd_list():
    model_dir = BASE_DIR / "model"
    if not model_dir.exists():
        print("  model/ 폴더가 없습니다.")
        return
    for d in sorted(model_dir.iterdir()):
        if d.is_dir():
            has_run = "run.py ✓" if (d / "run.py").exists() else "run.py 없음"
            print(f"  - model/{d.name:<22} {has_run}")
    print("  (작업 대상은 대화에서 폴더명으로 지정하세요.)")


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
#  content 정규화 (Anthropic thinking 블록 등 처리)
# -------------------------------------------------------------
def _extract_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        ).strip()
    return str(content)


# -------------------------------------------------------------
#  대화 루프
# -------------------------------------------------------------
def chat_loop(cfg: dict, provider: dict, agent):
    try:
        from rich.console import Console
        from rich.markdown import Markdown
        from rich.live import Live
        from rich.spinner import Spinner
        from rich.text import Text
        console = Console()
        USE_RICH = True
    except ImportError:
        console = None
        USE_RICH = False

    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.styles import Style
        pt_style = Style.from_dict({"prompt": "bold ansicyan"})
        session = PromptSession(style=pt_style)
        USE_PT = True
    except ImportError:
        USE_PT = False

    history = []
    last_log: dict = {}
    SEP = "[cyan]" + "─" * 52 + "[/cyan]" if USE_RICH else "─" * 52

    def print_sep():
        if USE_RICH:
            console.print(SEP)
        else:
            print("─" * 52)

    while True:
        try:
            if USE_PT:
                user_input = session.prompt("❯ ").strip()
            elif USE_RICH:
                console.print("[bold cyan]❯[/bold cyan] ", end="")
                user_input = input().strip()
            else:
                user_input = input("❯ ").strip()
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
            elif cmd in ("/help", "/?"):
                _cmd_help()
            elif cmd == "/config":
                _cmd_config(cfg, provider)
            elif cmd == "/list":
                _cmd_list()
            elif cmd == "/log":
                _cmd_log(last_log)
            elif cmd == "/llm":
                chosen = _cmd_llm(cfg, provider)
                if chosen:
                    try:
                        print(f"  {chosen['name']} 연결 확인 중...")
                        _build_chat_model(chosen, timeout=15).invoke([{"role": "user", "content": "hi"}])
                        provider = chosen
                        agent = load_agent(provider)
                        print(f"  전환 완료 → {provider['name']}")
                    except Exception as e:
                        show_error(e, last_log)
            elif cmd == "/reload":
                cfg = load_config()
                apply_pip_index(cfg)
                new_p = get_default_provider(cfg)
                for p in get_providers(cfg):
                    if p.get("name") == provider.get("name"):
                        new_p = p
                        break
                try:
                    _build_chat_model(new_p, timeout=15).invoke([{"role": "user", "content": "hi"}])
                    provider = new_p
                    agent = load_agent(provider)
                    print(f"  재로드 완료 (LLM: {provider['name']})")
                except Exception as e:
                    show_error(e, last_log)
                    print("  (기존 세션은 유지됩니다)")
            elif cmd == "/clear":
                history = []
                print("  대화 히스토리를 초기화했습니다.")
            else:
                print("  알 수 없는 명령입니다. /help 또는 /? 를 입력하세요.")
            continue

        # 에이전트 호출
        history.append({"role": "user", "content": user_input})
        try:
            import threading
            t0 = time.time()
            result_box = [None]
            error_box  = [None]

            def _invoke():
                try:
                    result_box[0] = agent.invoke({"messages": history})
                except Exception as ex:
                    error_box[0] = ex

            thread = threading.Thread(target=_invoke, daemon=True)
            thread.start()

            if USE_RICH:
                spin_frames = ["🐳 생각 중   ", "🐳 생각 중.  ", "🐳 생각 중.. ", "🐳 생각 중..."]
                fi = 0
                with Live(console=console, refresh_per_second=4, transient=True) as live:
                    while thread.is_alive():
                        live.update(Text(spin_frames[fi % len(spin_frames)], style="dim cyan"))
                        fi += 1
                        time.sleep(0.25)
            else:
                thread.join()

            thread.join()
            elapsed = time.time() - t0

            if error_box[0]:
                raise error_box[0]

            messages = result_box[0]["messages"]
            answer   = _extract_text(messages[-1].content)
            history  = messages

            print()
            print_sep()
            print()
            if USE_RICH:
                console.print("🐳 ", style="dim cyan", end="")
                console.print(Markdown(answer))
            else:
                print(f"🐳 {answer}")
            console.print(f"  [grey50]({elapsed:.1f}s)[/grey50]") if USE_RICH else print(f"  ({elapsed:.1f}s)")
            print()
            print_sep()
            print()
        except Exception as e:
            show_error(e, last_log)
            history.pop()


if __name__ == "__main__":
    main()
