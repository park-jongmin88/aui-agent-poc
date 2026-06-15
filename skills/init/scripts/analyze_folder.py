"""
skills/init/scripts/analyze_folder.py

workspace/models/<folder> 를 스캔해 파일 유형과 권장 모드를 분석한다.
에이전트가 이 결과를 바탕으로 run.py 생성 전략을 결정한다.
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from skills.common import ok, fail, MODELS_DIR, list_model_folders

MODEL_EXTENSIONS = {
    "sklearn": [".pkl", ".joblib"],
    "pytorch": [".pt", ".pth"],
    "tensorflow": [".h5", ".keras", ".pb"],
    "data": [".csv", ".parquet", ".xlsx", ".json", ".npy", ".npz"],
    "code": [".py", ".ipynb"],
}


def analyze(folder_name_or_no: str):
    # 번호 또는 이름으로 폴더 찾기
    folders = list_model_folders()
    target = None
    if str(folder_name_or_no).isdigit():
        no = int(folder_name_or_no)
        target = next((f for f in folders if f["no"] == no), None)
    else:
        target = next((f for f in folders if f["name"] == folder_name_or_no), None)

    if not target:
        # 폴더 목록 반환 (선택 안 된 경우)
        ok({
            "action": "list",
            "folders": folders,
            "message": "작업할 폴더를 선택해주세요:\n" +
                "\n".join(f"  {f['no']}) {f['name']}" +
                          (" ✓ run.py 있음" if f['has_run_py'] else "") for f in folders)
        })
        return

    folder = Path(target["path"])
    files = list(folder.iterdir()) if folder.exists() else []

    # 파일 분류
    found = {k: [] for k in MODEL_EXTENSIONS}
    found["other"] = []
    for f in files:
        if f.is_file():
            classified = False
            for category, exts in MODEL_EXTENSIONS.items():
                if f.suffix.lower() in exts:
                    found[category].append(f.name)
                    classified = True
                    break
            if not classified:
                found["other"].append(f.name)

    # 모드 추천
    if found["sklearn"]:
        mode = "LOAD_MODEL"
        framework = "sklearn"
        reason = f"학습된 모델 파일 발견: {found['sklearn']}"
    elif found["pytorch"]:
        mode = "LOAD_MODEL"
        framework = "pytorch"
        reason = f"PyTorch 모델 파일 발견: {found['pytorch']}"
    elif found["tensorflow"]:
        mode = "LOAD_MODEL_FOLDER"
        framework = "tensorflow"
        reason = f"TensorFlow 모델 파일 발견: {found['tensorflow']}"
    elif found["code"]:
        mode = "RUN_CODE"
        framework = "custom"
        reason = f"코드 파일 발견: {found['code']}"
    elif found["data"]:
        mode = "DATA_ONLY"
        framework = "sklearn"
        reason = f"데이터 파일만 발견: {found['data']}"
    else:
        mode = "DATA_ONLY"
        framework = "sklearn"
        reason = "빈 폴더 — 기본 템플릿 사용"

    has_run_py = (folder / "run.py").exists()

    ok({
        "action": "analyze",
        "folder": target["name"],
        "path": str(folder),
        "mode": mode,
        "framework": framework,
        "files": found,
        "has_run_py": has_run_py,
        "message": (
            f"폴더 분석 완료: workspace/models/{target['name']}\n"
            f"  파일: {sum(len(v) for v in found.values())}개\n"
            f"  추천 모드: {mode} ({reason})\n"
            f"  프레임워크: {framework}\n"
            + ("  ⚠ run.py 이미 존재 — 덮어쓸까요?" if has_run_py else "  → run.py 생성 준비됨")
        )
    })


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    analyze(arg)
