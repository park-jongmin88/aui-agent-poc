"""Fixed Ai Studio process contract.

Do not rename, reorder, add, or remove steps without also updating the
official process image and all user-facing documentation.
"""

AI_STUDIO_PROCESS_STEPS = (
    "모델 목록 확인",
    "모델 선택",
    "환경 검증",
    "템플릿 변환",
    "원격 MLflow 등록 실행",
    "추론 테스트",
    "오류 재실행",
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
