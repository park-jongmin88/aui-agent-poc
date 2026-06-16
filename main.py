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
import json as _json

BASE_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = BASE_DIR / "workspace"
CONFIG_PATH = BASE_DIR / "config.json"
VERSION = "0.2.0 (POC)"

SAMPLE_CONFIG_JSON = {
    "llm": {
        "active": "my-llm",
        "providers": [
            {
                "name": "my-llm",
                "type": "openai",
                "base_url": "http://your-llm-server:8000/v1",
                "api_key": "your-api-key",
                "model": "your-model-name"
            }
        ]
    },
    "mlflow": {
        "tracking_uri": "",
        "username": "",
        "password": ""
    }
}

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
#  config.json 로딩 / 생성 / 마법사
# -------------------------------------------------------------
def load_config(create_if_missing: bool = True) -> dict:
    if not CONFIG_PATH.exists():
        if not create_if_missing:
            return {}
        CONFIG_PATH.write_text(
            _json.dumps(SAMPLE_CONFIG_JSON, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"        config.json 이 없어 새로 생성했습니다 → {CONFIG_PATH}")
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return _json.load(f) or {}


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
    """우선순위: OS 환경변수 > config.json"""
    if os.environ.get("PIP_INDEX_URL"):
        return
    url = ((cfg.get("pip") or {}).get("index_url") or "").strip()
    if url and not any(tok in url for tok in PLACEHOLDER_TOKENS):
        os.environ["PIP_INDEX_URL"] = url


def run_wizard(cfg: dict) -> dict:
    """대화형으로 LLM provider를 입력받아 config.json 저장."""
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

    # type 선택
    print("  LLM 타입을 선택하세요:")
    print("    1) openai    — OpenAI 호환 (groq, 사내 LLM, ollama 등)")
    print("    2) anthropic — Anthropic Claude API (사내 프록시 포함)")
    print()
    while True:
        t_sel = input("  타입 번호 [1]: ").strip() or "1"
        if t_sel in ("1", "2"):
            break
        say("  1 또는 2 를 입력하세요.", style="yellow")
    ptype = "openai" if t_sel == "1" else "anthropic"
    print()

    fields = [
        ("name",     "이름(별칭)        "),
        ("base_url", "주소(base_url)   "),
        ("api_key",  "API 키           "),
        ("model",    "모델명           "),
    ]
    values = {k: "" for k, _ in fields}

    def fetch_models(base_url: str, api_key: str) -> list:
        try:
            import urllib.request, json as _json
            url = base_url.rstrip("/") + "/models"
            req = urllib.request.Request(url, headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = _json.loads(resp.read())
            return sorted([m["id"] for m in data.get("data", [])])
        except Exception:
            return []

    def ask(key, label):
        suffix = " [my-llm]" if key == "name" else ""
        while True:
            hint = ""
            if key == "model" and ptype == "openai":
                hint = " (Enter=목록 조회)"
            elif key == "base_url" and ptype == "anthropic":
                hint = " (없으면 Enter — 공식 API 사용)"
            v = input(f"  {label}{suffix}{hint} : ").strip()

            if key == "base_url" and v and _looks_like_path(v):
                say("  ⚠ URL 형식이 아닌 것 같습니다. 다시 입력해주세요.", style="yellow")
                continue

            if key == "model" and not v and ptype == "openai":
                base = values.get("base_url", "").strip()
                akey = values.get("api_key", "").strip()
                if base and akey:
                    say("  모델 목록 조회 중...", style="grey50")
                    models = fetch_models(base, akey)
                    if models:
                        for i, m in enumerate(models, 1):
                            print(f"    {i}) {m}")
                        print()
                        sel = input("  번호 선택 (또는 직접 입력, Enter=건너뛰기): ").strip()
                        if sel.isdigit() and 1 <= int(sel) <= len(models):
                            values[key] = models[int(sel) - 1]
                            say(f"  → {values[key]}", style="cyan")
                            break
                        else:
                            values[key] = sel
                            break
                    else:
                        say("  ⚠ 목록 조회 실패. 직접 입력해주세요.", style="yellow")
                        continue
                else:
                    say("  (목록 조회 불가 — 직접 입력하거나 Enter로 건너뛰세요)", style="grey50")
                    values[key] = input(f"  {label} : ").strip()
                    break

            values[key] = v
            break

    for key, label in fields:
        ask(key, label)

    # 리뷰 & 수정 루프
    while True:
        print()
        say("  --- 입력 확인 ---", style="bold")
        print(f"   0) 타입              : {ptype}")
        for i, (key, label) in enumerate(fields, 1):
            shown = _mask(values[key]) if key == "api_key" and values[key] else (values[key] or "(미입력)")
            print(f"   {i}) {label}: {shown}")
        print()
        sel = input("  수정할 번호 (0=타입 변경, Enter=완료): ").strip()
        if not sel:
            break
        if sel == "0":
            print("  1) openai  2) anthropic")
            t2 = input("  타입 번호 [1]: ").strip() or "1"
            if t2 in ("1", "2"):
                ptype = "openai" if t2 == "1" else "anthropic"
        elif sel.isdigit() and 1 <= int(sel) <= len(fields):
            key, label = fields[int(sel) - 1]
            ask(key, label)
        else:
            say(f"  0~{len(fields)} 사이의 번호를 입력하세요.", style="yellow")

    # provider 구성
    name = values["name"] or "my-llm"
    provider = {"name": name, "type": ptype}
    if ptype == "anthropic":
        if values.get("base_url"):
            provider["base_url"] = values["base_url"]
    else:
        provider["base_url"] = values.get("base_url") or "http://your-llm-server:8000/v1"
    provider["api_key"] = values.get("api_key") or "your-api-key"
    provider["model"]   = values.get("model")   or "your-model-name"

    # 저장 전 빈 항목 확인
    empty_keys = [label.strip() for key, label in fields if not values.get(key)]
    if empty_keys:
        print()
        say(f"  ⚠ 비워둔 항목: {', '.join(empty_keys)}", style="yellow")
        confirm = input("  비워둔 항목이 있습니다. 그래도 저장할까요? [y/N]: ").strip().lower()
        if confirm not in ("y", "yes"):
            say("  저장을 취소했습니다. config.json 을 직접 수정하거나 다시 실행하세요.", style="yellow")
            return load_config()

    # 텍스트 블록 교체 저장 (주석/샘플 영역 보존, bak 없음)
    _save_provider_to_config(name, ptype, provider)
    cfg = load_config()

    print()
    if is_placeholder(provider):
        say(f"  ⚠ 비워둔 항목이 있습니다. [yellow]{CONFIG_PATH}[/yellow] 를 열어 TODO 값을 채워주세요.", style="yellow")
        say(f"  재설정: ./install.sh 재실행 또는 config.json 직접 수정 후 ./start.sh")
    else:
        say(f"  ✓ 저장 완료 → {CONFIG_PATH}", style="green")
    say(f"  (추가 LLM 등록·수정은 {CONFIG_PATH} 직접 편집 후 CLI에서 /reload)")
    print()
    return cfg


def _save_provider_to_config(name: str, ptype: str, provider: dict):
    """config.json의 providers에 추가/교체 저장."""
    cfg = load_config()
    if "llm" not in cfg:
        cfg["llm"] = {}
    cfg["llm"]["active"] = name
    existing = [p for p in (cfg["llm"].get("providers") or []) if p.get("name") != name]
    existing.insert(0, provider)
    cfg["llm"]["providers"] = existing
    CONFIG_PATH.write_text(
        _json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8"
    )

def _read_requirements(req_path):
    """requirements.txt에서 설치할 패키지 목록을 읽는다.
    주석(#)과 빈 줄, -r/-e 등 옵션 줄은 건너뛴다."""
    pkgs = []
    try:
        for raw in req_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("-"):  # -r, -e, --hash 등 옵션 줄
                continue
            # 인라인 주석 제거
            if " #" in line:
                line = line.split(" #")[0].strip()
            if line:
                pkgs.append(line)
    except Exception:
        pass
    return pkgs


def _pkg_display_name(spec: str) -> str:
    """버전 지정자를 떼고 패키지 이름만 추출 (표시용)."""
    for sep in ("==", ">=", "<=", "~=", ">", "<", "!=", "["):
        idx = spec.find(sep)
        if idx > 0:
            return spec[:idx].strip()
    return spec.strip()


def _install_one(pip_exe, spec, extra_args):
    """패키지 1개 설치. Windows/Linux 공통, 인터럽트 안전.
    스피너 스레드 없이 단순 출력 (스피너가 Windows 콘솔에서 인터럽트 유발 가능).
    (성공여부, 출력텍스트) 반환."""
    cmd = [pip_exe, "-m", "pip", "install",
           "--no-input", "--disable-pip-version-check"] + extra_args + [spec]

    name = _pkg_display_name(spec)
    start = time.time()

    # 설치 시작 안내 (스피너 없이 한 줄)
    try:
        sys.stdout.write(f"    · {name} 설치 중... (시간이 걸릴 수 있습니다)\n")
        sys.stdout.flush()
    except Exception:
        pass

    proc = None
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        # communicate를 인터럽트로부터 보호:
        # Windows 콘솔에서 들어오는 우발적 KeyboardInterrupt에도
        # 설치 프로세스를 죽이지 않고 끝까지 기다린다.
        out = None
        while True:
            try:
                out, _ = proc.communicate()
                break
            except KeyboardInterrupt:
                continue

        elapsed = int(time.time() - start)
        text = out.decode("utf-8", errors="replace") if out else ""
        ok = proc.returncode == 0

        mark = "✓" if ok else "✗"
        try:
            sys.stdout.write(f"    {mark} {name}".ljust(50) + f"({elapsed}s)\n")
            sys.stdout.flush()
        except Exception:
            pass
        return ok, text
    except Exception as e:
        if proc:
            try: proc.kill()
            except Exception: pass
        try:
            sys.stdout.write(f"    ✗ {name} 오류: {e}\n")
            sys.stdout.flush()
        except Exception:
            pass
        return False, str(e)


def _normalize_pkg(name: str) -> str:
    """패키지 이름 정규화 (비교용): 소문자 + - _ 통일."""
    return name.lower().replace("_", "-").strip()


def _check_wheels_coverage(wheel_dir, pkgs):
    """wheels/ 폴더가 requirements의 주요 패키지를 커버하는지 느슨하게 체크.
    버전 무시, 패키지 이름만 비교. (전부있음 여부, 빠진목록) 반환."""
    try:
        if not wheel_dir.exists():
            return False, [_pkg_display_name(p) for p in pkgs]
        # wheels/ 안의 모든 .whl 파일명에서 패키지명 추출
        wheel_names = set()
        for f in wheel_dir.iterdir():
            if f.suffix == ".whl":
                # 파일명: {name}-{version}-... → 첫 토큰이 이름
                base = f.name.split("-")[0]
                wheel_names.add(_normalize_pkg(base))
            elif f.suffix in (".gz", ".zip"):  # sdist (tar.gz)
                base = f.name.rsplit("-", 1)[0] if "-" in f.name else f.name
                wheel_names.add(_normalize_pkg(base))

        missing = []
        for spec in pkgs:
            name = _normalize_pkg(_pkg_display_name(spec))
            if name not in wheel_names:
                missing.append(_pkg_display_name(spec))
        return (len(missing) == 0), missing
    except Exception:
        return False, [_pkg_display_name(p) for p in pkgs]


def _run_download_wheels() -> bool:
    """download_wheels 스크립트를 자동 실행해 wheels/ 를 채운다."""
    if os.name == "nt":
        script = BASE_DIR / "setting" / "download_wheels.bat"
        cmd = [str(script)]
        shell = True
    else:
        script = BASE_DIR / "setting" / "download_wheels.sh"
        cmd = ["bash", str(script)]
        shell = False

    if not script.exists():
        print(f"  🐳 [경고] {script.name} 를 찾을 수 없습니다.")
        return False

    print(f"  🐳 wheels/ 폴더가 없거나 부족 — wheel을 먼저 받습니다...")
    try:
        # download_wheels는 자체 출력이 있으므로 그대로 보여줌
        proc = subprocess.Popen(cmd, shell=shell, cwd=str(BASE_DIR))
        while True:
            try:
                proc.wait()
                break
            except KeyboardInterrupt:
                continue
        return proc.returncode == 0
    except Exception as e:
        print(f"  🐳 [경고] wheel 다운로드 실패: {e}")
        return False


def install_dependencies(show_header: bool = True) -> bool:
    req = BASE_DIR / "setting" / "requirements.txt"

    if os.name == "nt":
        venv_python = BASE_DIR / ".venv" / "Scripts" / "python.exe"
    else:
        venv_python = BASE_DIR / ".venv" / "bin" / "python"

    pip_exe = str(venv_python) if venv_python.exists() else sys.executable

    pkgs = _read_requirements(req)
    wheel_dir = BASE_DIR / "wheels"

    # ── wheel 우선 정책 ────────────────────────────────────────
    # 1. wheels/ 가 requirements를 충분히 커버하면 → wheel에서 설치
    # 2. 없거나 부족하면 → download_wheels 자동 실행 후 wheel에서 설치
    use_wheel = False
    if pkgs:
        covered, missing = _check_wheels_coverage(wheel_dir, pkgs)
        if covered:
            use_wheel = True
            if show_header:
                print("  🐳 wheels/ 폴더 확인 — 로컬 wheel로 설치합니다.")
        else:
            # wheel 받기 시도
            if _run_download_wheels():
                covered2, _ = _check_wheels_coverage(wheel_dir, pkgs)
                use_wheel = covered2
            if not use_wheel and show_header:
                print("  🐳 wheel 준비 미완료 — 인덱스(넥서스/PyPI)에서 설치합니다.")

    extra_args = []
    if os.environ.get("PIP_INDEX_URL"):
        extra_args += ["--index-url", os.environ["PIP_INDEX_URL"]]
    if use_wheel:
        # wheel에서만 설치 (네트워크 없이): --no-index + --find-links
        extra_args += ["--no-index", "--find-links", str(wheel_dir)]

    if show_header:
        print("  🐳 [3/4] 의존성 설치 중...")

    if not pkgs:
        # 목록을 못 읽으면 기존 방식(-r 일괄)으로 폴백
        try:
            cmd = [pip_exe, "-m", "pip", "install", "--no-input",
                   "--disable-pip-version-check", "-r", str(req)] + extra_args
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            out, _ = proc.communicate()
            ok = proc.returncode == 0
        except Exception:
            ok = False
        print(f"  🐳 [3/4] 의존성 설치             {'✓' if ok else '✗ 실패'}")
        return ok

    # 패키지별 개별 설치
    all_ok = True
    failed = []
    for spec in pkgs:
        try:
            ok, out = _install_one(pip_exe, spec, extra_args)
            if not ok:
                all_ok = False
                failed.append((_pkg_display_name(spec), out))
        except KeyboardInterrupt:
            print("  🐳 설치가 중단되었습니다. 다시 install을 실행해주세요.")
            return False

    if all_ok:
        print(f"  🐳 [3/4] 의존성 설치             ✓")
    else:
        print(f"  🐳 [3/4] 의존성 설치             ✗ 실패")
        for name, out in failed:
            tail = "\n".join(out.splitlines()[-3:]) if out else ""
            print(f"    ✗ {name} 설치 실패")
            if tail:
                for t in tail.splitlines():
                    print(f"        {t}")
    return all_ok


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
        console.print("  자연어로 요청하세요. 작업 순서 예시:")
        console.print('    [grey50]1) "sklearn_sample 준비해줘"       → 폴더 분석 후 run.py 생성[/grey50]')
        console.print('    [grey50]2) "검증해줘"                       → run.py 구조 검증[/grey50]')
        console.print('    [grey50]3) "학습 시작해줘"                  → 학습 실행 + MLflow 등록[/grey50]')
        console.print('    [grey50]4) "결과 확인해줘"                  → 추론 테스트[/grey50]')
        print()
        console.print("  명령어 목록은 [cyan]/help[/cyan] 또는 [cyan]/?[/cyan] 입력")
    except ImportError:
        print("  🐳  aiu-agent")
        print("  AI STUDIO 자동화 어시스턴트")
        print()
        print(f"  LLM: {provider['name']} ({provider['model']})")
        print()
        print("  자연어로 요청하세요. 작업 순서 예시:")
        print('    1) "sklearn_sample 준비해줘"       → 폴더 분석 후 run.py 생성')
        print('    2) "검증해줘"                       → run.py 구조 검증')
        print('    3) "학습 시작해줘"                  → 학습 실행 + MLflow 등록')
        print('    4) "결과 확인해줘"                  → 추론 테스트')
        print()
        print("  명령어 목록은 /help 또는 /? 입력")
    print()


# (group, cmd, desc) — group이 같으면 첫 행에만 표시 (병합 셀 느낌)
HELP_ITEMS = [
    ("작업",  "/list",    "작업 목록"),
    ("작업",  "/log",     "마지막 로그"),
    ("LLM",   "/llm",     "LLM 목록 + 전환"),
    ("LLM",   "/reload",  "설정 재로드"),
    ("LLM",   "/config",  "현재 설정"),
    ("세션",  "/clear",   "대화 초기화"),
    ("세션",  "/exit",    "종료"),
    ("",      "/? /help", "도움말"),
]


def _show_resume_hint():
    """시작 시 마지막 작업 폴더와 상태를 안내한다."""
    try:
        from skills.common import get_current_folder, get_state
        folder = get_current_folder()
        if not folder:
            return
        state = get_state(folder)
        if not state:
            return

        status_map = {
            "initialized": "run.py 생성 완료 → 검증 필요",
            "validated":   "검증 완료 → 학습 실행 가능",
            "trained":     "학습 완료 → 추론 테스트 가능",
            "predicted":   "추론 테스트 완료 → 배포 가능",
        }
        status = state.get("status", "")
        next_step = status_map.get(status, "")
        last_at = (state.get("last_run_at", "")[:16].replace("T", " ")
                   if state.get("last_run_at") else "")

        try:
            from rich.console import Console
            from rich.panel import Panel
            console = Console()
            body = f"[cyan]{folder.name}[/cyan]"
            if last_at:
                body += f"  [grey50]({last_at})[/grey50]"
            if next_step:
                body += f"\n→ {next_step}"
            if state.get("last_run_id"):
                body += f"\n  run_id: [grey50]{state['last_run_id']}[/grey50]"
            console.print(Panel(body, title="🐳 마지막 작업", border_style="cyan", width=60))
            print()
        except ImportError:
            print(f"  🐳 마지막 작업: {folder.name}")
            if next_step:
                print(f"     → {next_step}")
            print()
    except Exception:
        pass


# -------------------------------------------------------------
#  에러 분류
# -------------------------------------------------------------
ERROR_GUIDES = [
    ("tool_use_failed", "LLM이 도구 호출 형식을 잘못 생성했습니다 (모델 호환성 문제).\n"
                         "    다른 LLM(예: GPT-4 계열)을 쓰면 줄어듭니다. /llm 으로 전환해보세요."),
    ("401", "API 키가 올바르지 않습니다. config.json 의 api_key 를 확인하세요."),
    ("authentication", "API 키가 올바르지 않습니다. config.json 의 api_key 를 확인하세요."),
    ("404", "모델을 찾을 수 없습니다. config.json 의 model 값을 확인하세요."),
    ("model_not_found", "모델을 찾을 수 없습니다. config.json 의 model 값을 확인하세요."),
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
        c.print("   AI STUDIO 자동화 어시스턴트", style="grey50")
        c.print("=" * 52, style="grey50")
    except ImportError:
        print("=" * 52)
        print(f"   aiu-agent  v{VERSION}")
        print("   AI STUDIO 자동화 어시스턴트")
        print("=" * 52)
    print()


# -------------------------------------------------------------
#  엔트리
# -------------------------------------------------------------
def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    _banner()

    # [1/4] Python/가상환경 (여기 도달했으면 통과)
    print("  🐳 [1/4] Python / 가상환경       ✓")

    if mode == "--setup":
        # 설치 모드: 의존성 설치 + config.json 생성만 (마법사/LLM체크 없음)
        # stdin이 오염될 수 있으므로 입력을 일절 받지 않음
        print("  🐳 [2/4] 설정(config.json)        ", end="")
        cfg = load_config()  # 없으면 자동 생성
        apply_pip_index(cfg)
        print("✓ (생성됨)" if not CONFIG_PATH.exists() else "✓")

        print("  🐳 [3/4] 의존성 설치 중...")
        if not install_dependencies(show_header=False):
            sys.exit(1)
        generate_run_scripts()

        print()
        print("  설치 완료! start.bat (또는 ./start.sh) 으로 실행하세요.")
        print(f"  LLM 정보를 미리 설정하려면 {CONFIG_PATH} 를 편집하세요.")
        return

    # --check 또는 일반 실행
    # [2/4] 설정 확인 (없거나 placeholder면 마법사)
    cfg = check_config(interactive=(mode != "--check"))
    if cfg is None:
        sys.exit(1)
    apply_pip_index(cfg)

    # [3/4] 의존성 (이미 설치됨)
    print("  🐳 [3/4] 의존성                  ✓")

    # [4/4] 필수 체크 목록
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
    _show_resume_hint()
    chat_loop(cfg, provider, agent)


def check_config(interactive: bool = True):
    """[2/4] config.json 확인. placeholder면 마법사 진행 또는 안내."""
    cfg = load_config()
    apply_pip_index(cfg)
    provider = get_default_provider(cfg)

    if not is_placeholder(provider):
        print("  🐳 [2/4] 설정(config.json)       ✓")
        return cfg

    if not interactive:
        print("  🐳 [2/4] 설정(config.json)       ✗ 아직 설정되지 않았습니다.")
        print(f"        {CONFIG_PATH} 의 TODO 항목을 채운 뒤 다시 실행해주세요.")
        return None

    cfg = run_wizard(cfg)
    if not is_placeholder(get_default_provider(cfg)):
        print("  🐳 [2/4] 설정(config.json)       ✓")
        return cfg
    print("  🐳 [2/4] 설정(config.json)       ✗ 필수 항목이 비어있습니다.")
    print(f"        {CONFIG_PATH} 를 열어 TODO 항목을 채운 뒤 ./start.sh 로 재실행하세요.")
    print(f"        또는 ./install.sh 를 다시 실행하세요.")
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
    from langchain_core.messages import HumanMessage
    providers = get_providers(cfg)
    provider = get_default_provider(cfg)

    while True:
        try:
            _build_chat_model(provider, timeout=15).invoke([HumanMessage(content="hi")])
            print(f"  🐳 [4/4] LLM 연결 ({provider['name']})        ✓")
            return provider
        except AttributeError:
            # 응답 파싱 오류 (프록시 응답 포맷 불일치 등) — 연결은 된 것으로 간주
            print(f"  🐳 [4/4] LLM 연결 ({provider['name']})        ✓")
            return provider
        except Exception as e:
            print(f"  🐳 [4/4] LLM 연결 ({provider['name']})        ✗")
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
        ptype = provider.get("type", "openai")
        base  = provider.get("base_url", "(없음)")
        model = provider.get("model", "(없음)")
        print()
        print("  ┌─ 연결 정보 확인 ───────────────────────────────")
        print(f"  │  이름    : {provider.get('name')}")
        print(f"  │  type    : {ptype}")
        if ptype != "anthropic" or base != "(없음)":
            print(f"  │  base_url: {base}")
        print(f"  │  model   : {model}")
        print("  └────────────────────────────────────────────────")
        print()
        print("  LLM 연결이 되어야 진행할 수 있습니다.")
        print("  해결 방법:")
        print(f"    1) {CONFIG_PATH} 를 열어 LLM 정보 수정 후 ./start.sh 재실행")
        print(f"    2) ./install.sh 재실행 후 마법사에서 다시 입력")
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
        tbl.add_column("구분",   style="bold cyan", min_width=6)
        tbl.add_column("명령어", min_width=12)
        tbl.add_column("설명")
        prev_group = None
        for group, cmd, desc in HELP_ITEMS:
            g_label = f"[bold cyan]{group}[/bold cyan]" if group and group != prev_group else ""
            tbl.add_row(g_label, cmd, desc)
            prev_group = group
        console.print(tbl)
        print()
    except ImportError:
        print()
        prev_group = None
        for group, cmd, desc in HELP_ITEMS:
            if group and group != prev_group:
                print(f"  [{group}]")
            print(f"    {cmd:<12} {desc}")
            prev_group = group
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
    model_dir = WORKSPACE_DIR / "models"
    if not model_dir.exists():
        print("  workspace/models/ 폴더가 없습니다.")
        return
    folders = sorted([d for d in model_dir.iterdir() if d.is_dir()])
    if not folders:
        print("  작업 폴더가 없습니다. workspace/models/ 에 폴더를 추가하세요.")
        return
    try:
        from rich.console import Console
        from rich.table import Table
        from rich import box as rich_box
        console = Console()
        tbl = Table(box=rich_box.SIMPLE_HEAVY, show_header=True, header_style="bold")
        tbl.add_column("번호", style="cyan", min_width=4)
        tbl.add_column("폴더명", min_width=24)
        tbl.add_column("run.py", min_width=10)
        tbl.add_column("파일 목록")
        for i, d in enumerate(folders, 1):
            has_run = "[green]✓ 있음[/green]" if (d / "run.py").exists() else "[grey50]없음[/grey50]"
            files = [f.name for f in d.iterdir() if f.is_file()]
            file_str = ", ".join(files[:3]) + ("..." if len(files) > 3 else "") if files else "(비어있음)"
            tbl.add_row(str(i), d.name, has_run, file_str)
        console.print(tbl)
    except ImportError:
        for i, d in enumerate(folders, 1):
            has_run = "run.py ✓" if (d / "run.py").exists() else "run.py 없음"
            print(f"  {i}) {d.name:<24} {has_run}")
    print()
    print("  번호나 이름으로 지정하세요. 예: '1번 준비해줘', 'sklearn_sample 학습해줘'")


def _cmd_llm(cfg: dict, current: dict):
    """등록 LLM 목록 표시 + 번호 선택으로 전환. 전환 시 (provider) 반환."""
    usable = [p for p in get_providers(cfg) if not is_placeholder(p)]
    if not usable:
        print("  사용 가능한 LLM이 없습니다. config.json 을 확인하세요.")
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
def _get_toolbar_text(provider: dict) -> str:
    """bottom_toolbar 텍스트 생성 — 현재 모델 + 단계 네비게이션."""
    try:
        sys.path.insert(0, str(BASE_DIR))
        from skills.common import get_current_folder, get_state
        folder = get_current_folder()
        folder_name = folder.name if folder else "없음"
        status = get_state(folder).get("status", "") if folder else ""
    except Exception:
        folder_name = "없음"
        status = ""

    STAGES = [
        ("init",     "initialized"),
        ("validate", "validated"),
        ("train",    "trained"),
        ("predict",  "predicted"),
        ("deploy",   "deployed"),
    ]

    STATUS_ORDER = ["initialized", "validated", "local_tested", "trained", "predicted", "deployed"]

    def stage_icon(stage_name: str, required_status: str) -> str:
        if not status:
            if stage_name == "init":
                return "<ansicyan><b>[init]</b></ansicyan>"
            return f"<ansiwhite>{stage_name}</ansiwhite>"

        try:
            current_idx = STATUS_ORDER.index(status) if status in STATUS_ORDER else -1
            required_idx = STATUS_ORDER.index(required_status) if required_status in STATUS_ORDER else -1
        except ValueError:
            current_idx = required_idx = -1

        if status == required_status or (stage_name == "init" and status in STATUS_ORDER):
            if stage_name == "deploy" and status == "deployed":
                return "<ansigreen>✅deploy</ansigreen>"
            if current_idx > required_idx:
                return f"<ansigreen>✅{stage_name}</ansigreen>"
            elif current_idx == required_idx:
                return f"<ansicyan><b>[{stage_name}]</b></ansicyan>"
        if current_idx > required_idx:
            return f"<ansigreen>✅{stage_name}</ansigreen>"
        elif current_idx == required_idx - 1 or (stage_name == "init" and not status):
            return f"<ansicyan><b>[{stage_name}]</b></ansicyan>"
        elif status == "error":
            return f"<ansired>❌{stage_name}</ansired>"
        else:
            return f"<ansiwhite>{stage_name}</ansiwhite>"

    nav_parts = []
    for i, (sname, sstat) in enumerate(STAGES):
        nav_parts.append(stage_icon(sname, sstat))
        if i < len(STAGES) - 1:
            nav_parts.append("<ansiwhite> ──▶ </ansiwhite>")

    llm_name = provider.get("name", "?")
    model_name = provider.get("model", "?")
    short_model = model_name.split("/")[-1] if "/" in model_name else model_name
    if len(short_model) > 20:
        short_model = short_model[:20] + "…"

    nav = "".join(nav_parts)
    return f"━━━ 📁 {folder_name}  │  {nav}  │  {llm_name}: {short_model} ━━━"


def chat_loop(cfg: dict, provider: dict, agent):
    try:
        from rich.console import Console
        from rich.markdown import Markdown
        from rich.live import Live
        from rich.text import Text
        console = Console()
        USE_RICH = True
    except ImportError:
        console = None
        USE_RICH = False

    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.styles import Style
        from prompt_toolkit.formatted_text import HTML

        pt_style = Style.from_dict({
            "prompt": "bold ansicyan",
            "bottom-toolbar": "bg:#1a1a2e #aaaaaa",
        })

        def get_toolbar():
            return HTML(_get_toolbar_text(provider))

        session = PromptSession(
            style=pt_style,
            bottom_toolbar=get_toolbar,
        )
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
                # provider가 변경될 수 있으므로 매번 toolbar 함수 재생성
                session.bottom_toolbar = lambda: HTML(_get_toolbar_text(provider))
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
                        from langchain_core.messages import HumanMessage
                        print(f"  {chosen['name']} 연결 확인 중...")
                        _build_chat_model(chosen, timeout=15).invoke([HumanMessage(content="hi")])
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
                    from langchain_core.messages import HumanMessage
                    _build_chat_model(new_p, timeout=15).invoke([HumanMessage(content="hi")])
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
