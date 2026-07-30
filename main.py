"""
==============================================================================
 AI-Studio 3.0 GenAI Agent - 메인 진입점
==============================================================================
 개선안(메뉴구조 개선)의 각 기능을 번호로 선택해 실행한다.
 아직 구현되지 않은 기능은 계획(PLAN.md) 안내만 출력한다.

 [사용]
   python main.py

 [구조]
   각 기능은 폴더로 분리돼 있다 (예: static_endpoint/, evaluation/ ...).
   폴더 안 run.py 가 있으면 그게 실제 실행 코드, PLAN.md 는 그 기능의
   설계/계획 정리 문서다. 폴더 하나하나가 나중에 독립적으로도 쓸 수 있게
   구성한다 (judge_register.py 처럼 단독 실행 가능한 형태 지향).
==============================================================================
"""

import importlib.util
import os

_HERE = os.path.dirname(os.path.abspath(__file__))

# #############################################################################
# 기능 레지스트리 - (표시 이름, 폴더명)
# #############################################################################

FEATURES = [
    ("Static Endpoint 생성",                 "static_endpoint"),
    ("통합 Hub / MLflow Spoke 연동",          "hub_spoke"),
    ("Langflow Import (유형1: 외부 파이프라인)", "langflow_import"),
    ("모델 등록 (유형2: AIU IDE)",             "model_register"),
    ("서빙 등록 (Inference / Custom LLM)",     "serving"),
    ("Evaluation / Trace 모니터링",           "evaluation"),
    ("Dataset 관리 (업로드→변환→등록)",        "dataset_builder"),
    ("Augmentation (데이터 증강)",             "augmentation"),
    ("Key / 보안 관리",                       "access_control"),
]


def _run_py_path(folder: str) -> str:
    return os.path.join(_HERE, folder, "run.py")


def _plan_md_path(folder: str) -> str:
    return os.path.join(_HERE, folder, "PLAN.md")


def _pick_number(prompt_text: str, count: int) -> int:
    while True:
        sel = input(prompt_text).strip()
        if sel.isdigit() and 1 <= int(sel) <= count:
            return int(sel)
        print("  올바른 번호를 입력하세요.")


def list_features():
    print("\n" + "=" * 60)
    print(" AI-Studio 3.0 GenAI Agent")
    print("=" * 60)
    for i, (label, folder) in enumerate(FEATURES, 1):
        has_run = os.path.exists(_run_py_path(folder))
        status = "" if has_run else "  (준비중)"
        print(f"  [{i}] {label}{status}")
    print("=" * 60)


def run_feature(folder: str, label: str):
    run_py = _run_py_path(folder)
    if os.path.exists(run_py):
        spec = importlib.util.spec_from_file_location(f"{folder}.run", run_py)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "main"):
            mod.main()
        else:
            print(f"[알림] {folder}/run.py 에 main() 이 없습니다.")
        return

    # 아직 구현 안 됨 -> 계획 문서 안내
    print(f"\n[준비중] '{label}' 기능은 아직 구현되지 않았습니다.")
    plan = _plan_md_path(folder)
    if os.path.exists(plan):
        print(f"  → 계획 문서: {folder}/PLAN.md")
        with open(plan, "r", encoding="utf-8") as f:
            head = f.read(400)
        print("  --- 미리보기 ---")
        print(" ", head.replace("\n", "\n  "), "...")
    else:
        print("  (계획 문서도 아직 없습니다.)")


def main():
    list_features()
    idx = _pick_number("번호 선택: ", len(FEATURES))
    label, folder = FEATURES[idx - 1]
    run_feature(folder, label)


if __name__ == "__main__":
    main()
