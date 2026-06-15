"""
skills/validate/scripts/validate_run.py

workspace/models/<folder>/run.py 의 구조와 내용을 검증한다.
- 구조: 9섹션 존재 여부
- 내용: TODO 미입력, MLflow 설정, 실험명/모델명 확인
"""
import sys
import re
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from skills.common import (
    ok, fail, get_current_folder, get_state, set_state,
    is_mlflow_configured, check_gate
)

REQUIRED_SECTIONS = [
    (1, "임포트"),
    (2, "MLflow"),
    (3, "데이터"),
    (4, "모델"),
    (5, "트레이닝|train"),
    (6, "인풋|input"),
    (7, "로깅|log"),
    (8, "config"),
    (9, "런|run|__main__"),
]


def validate(folder_name: str = None):
    # 폴더 결정
    if folder_name:
        from skills.common import MODELS_DIR
        folder = MODELS_DIR / folder_name
    else:
        folder = get_current_folder()

    if not folder or not folder.exists():
        fail("현재 작업 폴더가 없습니다. 폴더를 선택해주세요.")

    # 게이트 확인
    passed, msg = check_gate(folder, "validate")
    if not passed:
        fail(msg)

    run_py = folder / "run.py"
    if not run_py.exists():
        fail(
            f"workspace/models/{folder.name}/run.py 가 없습니다.\n"
            "먼저 init(준비)을 실행해주세요."
        )

    text = run_py.read_text(encoding="utf-8")
    lines = text.splitlines()

    issues = []
    warnings = []

    # ── 구조 검증: 9섹션 ──────────────────────────────────────
    missing_sections = []
    for no, pattern in REQUIRED_SECTIONS:
        found = re.search(
            rf"#\s*{no}\s*[\.\-].*({pattern})",
            text, re.IGNORECASE
        )
        if not found:
            missing_sections.append(f"섹션 {no} ({pattern})")

    if missing_sections:
        issues.append(f"누락된 섹션: {', '.join(missing_sections)}")

    # ── 내용 검증: TODO 미입력 ───────────────────────────────
    todo_items = []
    for i, line in enumerate(lines, 1):
        if "# TODO" in line:
            todo_items.append({"line": i, "content": line.strip()})

    if todo_items:
        issues.append(
            f"TODO 미입력 {len(todo_items)}개:\n" +
            "\n".join(f"    line {t['line']}: {t['content']}" for t in todo_items)
        )

    # ── 내용 검증: MLflow 설정 ───────────────────────────────
    uri_match = re.search(r'MLFLOW_TRACKING_URI\s*=\s*["\'](.+?)["\']', text)
    uri = uri_match.group(1) if uri_match else ""
    mlflow_ok = bool(uri) and "your-mlflow" not in uri and uri != ""

    if not mlflow_ok:
        issues.append("MLflow 서버 주소 미설정 (섹션 2의 MLFLOW_TRACKING_URI 확인)")

    # ── 내용 검증: 실험명/모델명 ─────────────────────────────
    exp_match = re.search(r'EXPERIMENT_NAME\s*=\s*["\'](.+?)["\']', text)
    exp = exp_match.group(1) if exp_match else ""
    if not exp or exp == "my-experiment":
        warnings.append("EXPERIMENT_NAME이 기본값입니다. 실험명을 변경하세요.")

    model_match = re.search(r'MODEL_NAME\s*=\s*["\'](.+?)["\']', text)
    model = model_match.group(1) if model_match else ""
    if not model or model == "my-model":
        warnings.append("MODEL_NAME이 기본값입니다. 모델명을 변경하세요.")

    # ── NotImplementedError 체크 ─────────────────────────────
    not_impl = []
    for i, line in enumerate(lines, 1):
        if "raise NotImplementedError" in line:
            not_impl.append(i)

    if not_impl:
        issues.append(
            f"NotImplementedError {len(not_impl)}개 (미구현 함수):\n" +
            "\n".join(f"    line {l}" for l in not_impl)
        )

    # ── 결과 ─────────────────────────────────────────────────
    passed = len(issues) == 0

    if passed:
        set_state(folder, status="validated", last_action="validate")
        message = (
            f"✓ 검증 통과 — workspace/models/{folder.name}/run.py\n"
            f"  섹션: 9/9 완료\n"
            f"  MLflow: {uri}\n"
            f"  실험명: {exp} / 모델명: {model}\n"
            + (f"\n  ⚠ 경고 {len(warnings)}개:\n" + "\n".join(f"    {w}" for w in warnings)
               if warnings else "")
            + "\n\n→ 로컬 테스트('로컬 실행해줘') 또는 바로 학습('학습 시작해줘') 가능합니다."
        )
    else:
        message = (
            f"✗ 검증 실패 — workspace/models/{folder.name}/run.py\n\n"
            + "\n\n".join(f"  [{i+1}] {issue}" for i, issue in enumerate(issues))
            + "\n\n→ 위 항목을 수정 후 다시 검증해주세요."
        )

    ok({
        "folder": folder.name,
        "passed": passed,
        "issues": issues,
        "warnings": warnings,
        "todo_items": todo_items,
        "mlflow_uri": uri,
        "experiment_name": exp,
        "model_name": model,
        "message": message,
    })


if __name__ == "__main__":
    folder_name = sys.argv[1] if len(sys.argv) > 1 else None
    validate(folder_name)
