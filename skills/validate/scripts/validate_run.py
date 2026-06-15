"""
skills/validate/scripts/validate_run.py

workspace/run.py 가 9-섹션 표준 구조를 따르는지 검증한다.
TODO 항목 미입력 여부도 확인한다.
"""
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from skills.common import ok, fail, RUN_PY

REQUIRED_SECTIONS = [
    ("1", "임포트"),
    ("2", "MLflow 연동"),
    ("3", "데이터 준비"),
    ("4", "모델 준비"),
    ("5", "트레이닝"),
    ("6", "인풋 샘플"),
    ("7", "MLflow.*로깅"),
    ("8", "config"),
    ("9", "런 스타트"),
]


def validate():
    if not RUN_PY.exists():
        fail(
            "workspace/run.py 가 없습니다.\n"
            "먼저 작업 폴더를 선택하고 준비(init)를 실행해주세요."
        )

    text = RUN_PY.read_text(encoding="utf-8")
    issues = []
    found_sections = []

    # 9섹션 확인
    for no, pattern in REQUIRED_SECTIONS:
        if re.search(rf"#\s*[-]+\s*\n#\s*{no}\.\s*{pattern}", text, re.IGNORECASE):
            found_sections.append(f"섹션 {no}")
        else:
            issues.append(f"섹션 {no}({pattern}) 누락 또는 형식 불일치")

    # TODO 미입력 확인
    todos = []
    for i, line in enumerate(text.splitlines(), 1):
        if "# TODO" in line and "your-" not in line.lower():
            # 실제 TODO가 아직 남은 경우
            todos.append(f"  line {i}: {line.strip()}")
        elif "your-" in line.lower() or "your-mlflow" in line.lower():
            todos.append(f"  line {i}: {line.strip()} ← 미입력")

    # MLflow URI 확인
    uri_match = re.search(r'MLFLOW_TRACKING_URI\s*=\s*["\'](.+?)["\']', text)
    uri = uri_match.group(1) if uri_match else ""
    mlflow_ok = bool(uri) and "your-mlflow" not in uri

    if issues:
        fail(
            "run.py 구조 검증 실패:\n" +
            "\n".join(f"  ✗ {i}" for i in issues) +
            (f"\n\nTODO 미입력 항목:\n" + "\n".join(todos) if todos else "")
        )

    ok({
        "sections": len(found_sections),
        "todos": todos,
        "mlflow_uri": uri,
        "mlflow_configured": mlflow_ok,
        "message": (
            f"✓ 9섹션 구조 확인 완료\n"
            f"  MLflow: {'✓ ' + uri if mlflow_ok else '✗ 미설정 (섹션 2 확인 필요)'}\n"
            + (f"  ⚠ TODO 미입력 {len(todos)}개:\n" + "\n".join(todos) if todos else "  ✓ TODO 항목 없음")
            + ("\n\n→ 학습을 시작해도 됩니다." if mlflow_ok and not todos else
               "\n\n→ 위 항목을 수정 후 다시 검증해주세요.")
        )
    })


if __name__ == "__main__":
    validate()
