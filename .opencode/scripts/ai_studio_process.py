"""Fixed Ai Studio process contract.

Do not rename, reorder, add, or remove steps without also updating the
official process image and all user-facing documentation.
"""

# --- Windows/CP949 콘솔에서도 한글이 깨지지 않도록 stdout/stderr를 UTF-8로 강제 ---
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
# --- end UTF-8 guard ---


AI_STUDIO_PROCESS_STEPS = (
    "모델 목록 확인",   # 1 - data/ 스캔 + Case 판별 (모델만/학습만/둘다)
    "모델 선택",        # 2 - 번호 선택. Case 3(둘다)이면 기존모델/새학습 물어봄
    "생성",             # 3 - Case에 맞는 템플릿 복사 + data 넣기
    "학습",             # 4 - Case 2/3-학습: 의존성체크 → train.py 실행 → saved_model 생성
    "로컬 추론",        # 5 - (선택) predict 호출로 등록 전 로컬 확인. 서빙 단어 안 씀
    "등록",             # 6 - (선택) MLflow log_model
    "원격 추론",        # 7 - 등록 후 원격 엔드포인트 테스트
)

if len(AI_STUDIO_PROCESS_STEPS) != 7:
    raise RuntimeError("Ai Studio process must stay exactly 7 steps")

TODO_GUIDE_BORDER = "=" * 60
TODO_GUIDE_TITLE = "Ai Studio - 7단계"
TODO_GUIDE_HINT = "숫자키로 선택한 단계 1개만 실행 / 모델 선택 화면에서만 숫자=모델 번호"
ANSI_YELLOW_BOLD = "\033[1;33m"
ANSI_RESET = "\033[0m"
MODEL_SELECTION_HINT_LINES = (
    '사용자는 숫자 예시 1번부터 선택합니다.',
    '자연어로도 선택할 수 있습니다. 예: "첫 번째 모델", "파이토치 모델", "data/... 사용".',
)


def normalize_todo_statuses(statuses: list[str] | tuple[str, ...] | None = None) -> tuple[str, ...]:
    default_statuses = (
        "대기",
        "대기",
        "사용자 선택",
        "사용자 선택",
        "사용자 선택",
        "사용자 선택",
        "사용자 선택",
    )
    if statuses is None:
        return default_statuses
    normalized = tuple(str(status) for status in statuses[:7])
    if len(normalized) < 7:
        normalized = normalized + default_statuses[len(normalized):]
    return normalized


def format_todo_guide(statuses: list[str] | tuple[str, ...] | None = None) -> str:
    normalized = normalize_todo_statuses(statuses)
    lines = [
        "",
        TODO_GUIDE_BORDER,
        TODO_GUIDE_TITLE,
        TODO_GUIDE_BORDER,
        TODO_GUIDE_HINT,
    ]
    for index, (title, status) in enumerate(zip(AI_STUDIO_PROCESS_STEPS, normalized), start=1):
        lines.append(f"[{index}] {title}: {status}")
    lines.append(TODO_GUIDE_BORDER)
    return "\n".join(lines)


def format_model_selection_hint(indent: str = "") -> str:
    return "\n".join(
        f"{indent}{ANSI_YELLOW_BOLD}{line}{ANSI_RESET}"
        for line in MODEL_SELECTION_HINT_LINES
    )
