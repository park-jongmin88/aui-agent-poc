"""
skills/init/scripts/generate_run.py

workspace/models/<folder>/source/ 를 분석해
workspace/models/<folder>/run.py 를 자동 생성한다.

사용:
    python skills/init/scripts/generate_run.py <폴더명> <실험명> <모델명>
"""
import sys
import re
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from skills.common import (
    ok, fail, MODELS_DIR, TEMPLATES_DIR, CONFIG_PATH,
    get_mlflow_config, get_state, set_state, set_current_folder, list_model_folders
)

# ── 파일 유형 정의 ──────────────────────────────────────────
MODEL_EXTENSIONS = {
    "sklearn":    [".pkl", ".joblib"],
    "pytorch":    [".pt", ".pth"],
    "tensorflow": [".h5", ".keras", ".pb"],
}
DATA_EXTENSIONS  = [".csv", ".parquet", ".xlsx", ".json", ".npy", ".npz"]
CODE_EXTENSIONS  = [".py", ".ipynb"]


def analyze_source(source_dir: Path) -> dict:
    """source/ 폴더 분석 → 모드/프레임워크 판별."""
    if not source_dir.exists():
        return {"mode": "TEMPLATE", "framework": "sklearn", "files": {}, "reason": "빈 폴더"}

    files = {
        "model":  [],
        "data":   [],
        "code":   [],
        "other":  [],
    }
    framework = "sklearn"

    for f in source_dir.iterdir():
        if not f.is_file():
            continue
        ext = f.suffix.lower()
        classified = False
        for fw, exts in MODEL_EXTENSIONS.items():
            if ext in exts:
                files["model"].append(f.name)
                framework = fw
                classified = True
                break
        if not classified:
            if ext in DATA_EXTENSIONS:
                files["data"].append(f.name)
            elif ext in CODE_EXTENSIONS:
                files["code"].append(f.name)
            else:
                files["other"].append(f.name)

    if files["model"]:
        mode = "LOAD_MODEL"
        reason = f"학습된 모델 파일 발견: {files['model']}"
    elif files["code"]:
        mode = "RUN_CODE"
        framework = "custom"
        reason = f"코드 파일 발견: {files['code']}"
    elif files["data"]:
        mode = "DATA_ONLY"
        reason = f"데이터 파일 발견: {files['data']}"
    else:
        mode = "TEMPLATE"
        reason = "빈 폴더 — 기본 템플릿 사용"

    return {"mode": mode, "framework": framework, "files": files, "reason": reason}


def read_source_code(source_dir: Path) -> str:
    """source/ 안의 .py 파일들을 읽어 합친다."""
    code_parts = []
    for f in source_dir.iterdir():
        if f.suffix == ".py" and f.is_file():
            code_parts.append(f"# === {f.name} ===\n" + f.read_text(encoding="utf-8", errors="replace"))
    return "\n\n".join(code_parts)


# ── 섹션별 코드 생성 ────────────────────────────────────────

def gen_section1(framework: str, mode: str, source_files: dict) -> str:
    """섹션 1: 임포트."""
    imports = ["import os", "import json", "from pathlib import Path", "", "import mlflow"]

    if framework == "sklearn":
        imports += [
            "",
            "from sklearn.ensemble import RandomForestClassifier  # TODO: 사용할 모델로 변경",
            "from sklearn.model_selection import train_test_split",
            "from sklearn.metrics import accuracy_score",
            "import joblib",
        ]
        if any(f.endswith(".csv") for f in source_files.get("data", [])):
            imports.append("import pandas as pd")
        if any(f.endswith(".npy") or f.endswith(".npz") for f in source_files.get("data", [])):
            imports.append("import numpy as np")

    elif framework == "pytorch":
        imports += [
            "",
            "import torch",
            "import torch.nn as nn",
            "import torch.optim as optim",
        ]

    elif framework == "tensorflow":
        imports += [
            "",
            "import tensorflow as tf",
        ]

    elif framework == "custom":
        imports += [
            "",
            "# TODO: source/ 코드에서 필요한 임포트 추가",
        ]

    return "\n".join(imports)


def gen_section2(folder_name: str, experiment_name: str, model_name: str) -> str:
    """섹션 2: MLflow 연동 (config.json에서 자동 채움)."""
    mlflow_cfg = get_mlflow_config()
    uri = mlflow_cfg.get("tracking_uri", "")
    username = mlflow_cfg.get("username", "")
    password = mlflow_cfg.get("password", "")

    uri_line = f'MLFLOW_TRACKING_URI = "{uri}"' if uri else 'MLFLOW_TRACKING_URI = ""  # TODO: MLflow 서버 주소'
    user_line = f'MLFLOW_USERNAME = "{username}"'
    pass_line = f'MLFLOW_PASSWORD = "{password}"'

    return f'''ROOT = Path(__file__).resolve().parents[2]  # 프로젝트 루트

{uri_line}
{user_line}
{pass_line}

mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
if MLFLOW_USERNAME:
    os.environ["MLFLOW_TRACKING_USERNAME"] = MLFLOW_USERNAME
    os.environ["MLFLOW_TRACKING_PASSWORD"] = MLFLOW_PASSWORD

EXPERIMENT_NAME = "{experiment_name}"
MODEL_NAME = "{model_name}"

mlflow.set_experiment(EXPERIMENT_NAME)'''


def gen_section3(mode: str, framework: str, source_files: dict, source_dir: Path) -> str:
    """섹션 3: 데이터 준비."""
    data_files = source_files.get("data", [])

    if mode == "LOAD_MODEL":
        # 모델이 있으면 데이터는 샘플 생성
        if framework == "sklearn":
            return '''def prepare_data():
    """샘플 데이터 생성 (모델 검증용)."""
    from sklearn.datasets import make_classification
    X, y = make_classification(n_samples=100, n_features=10, random_state=42)
    return train_test_split(X, y, test_size=0.2, random_state=42)'''
        else:
            return '''def prepare_data():
    # TODO: 검증용 샘플 데이터 준비
    raise NotImplementedError'''

    elif data_files:
        csv_files = [f for f in data_files if f.endswith(".csv")]
        if csv_files and framework == "sklearn":
            fname = csv_files[0]
            return f'''def prepare_data():
    """source/ 의 데이터 파일 로드."""
    data_path = ROOT / "workspace" / "models" / Path(__file__).parent.name / "source" / "{fname}"
    df = pd.read_csv(data_path)
    # TODO: 타겟 컬럼명 확인
    target_col = df.columns[-1]  # 마지막 컬럼을 타겟으로 가정
    X = df.drop(columns=[target_col]).values
    y = df[target_col].values
    return train_test_split(X, y, test_size=0.2, random_state=42)'''

    return '''def prepare_data():
    # TODO: 데이터 로딩/생성
    # 예) from sklearn.datasets import make_classification
    #     X, y = make_classification(n_samples=1000, n_features=10)
    #     return train_test_split(X, y, test_size=0.2)
    raise NotImplementedError'''


def gen_section4(mode: str, framework: str, source_files: dict, source_dir: Path) -> str:
    """섹션 4: 모델 준비."""
    model_files = source_files.get("model", [])

    if mode == "LOAD_MODEL" and model_files:
        mfile = model_files[0]
        mpath = f'ROOT / "workspace" / "models" / Path(__file__).parent.name / "source" / "{mfile}"'

        if framework == "sklearn":
            return f'''def build_model():
    """저장된 모델 로드."""
    model_path = {mpath}
    return joblib.load(model_path)'''

        elif framework == "pytorch":
            return f'''def build_model():
    """저장된 PyTorch 모델 로드."""
    model_path = {mpath}
    # TODO: 모델 클래스 정의 필요
    # model = MyModel()
    # model.load_state_dict(torch.load(model_path))
    # return model
    raise NotImplementedError  # TODO: 모델 클래스 정의 후 활성화'''

        elif framework == "tensorflow":
            return f'''def build_model():
    """저장된 TensorFlow 모델 로드."""
    model_path = {mpath}
    return tf.keras.models.load_model(str(model_path))'''

    elif mode == "RUN_CODE":
        code = read_source_code(source_dir)
        # 학습 함수 패턴 찾기
        train_funcs = re.findall(r'def\s+(train\w*|fit\w*|run\w*)\s*\(', code)
        hint = f"# 발견된 함수: {train_funcs}" if train_funcs else ""
        return f'''def build_model():
    {hint}
    # TODO: source/ 코드에서 모델 로드 또는 정의
    raise NotImplementedError'''

    # DATA_ONLY / TEMPLATE
    if framework == "sklearn":
        return '''def build_model():
    """기본 모델 정의."""
    # TODO: 사용할 모델로 변경 (현재: RandomForestClassifier 기본값)
    return RandomForestClassifier(n_estimators=100, random_state=42)'''
    else:
        return '''def build_model():
    # TODO: 모델 정의
    raise NotImplementedError'''


def gen_section5(mode: str, framework: str) -> str:
    """섹션 5: 트레이닝."""
    if mode == "LOAD_MODEL":
        if framework == "sklearn":
            return '''def train(model, X_train, y_train):
    """로드된 모델로 재학습 (또는 검증만)."""
    # TODO: 재학습 필요 없으면 pass, 필요하면 fit 실행
    model.fit(X_train, y_train)
    return model'''
        elif framework == "tensorflow":
            return '''def train(model, X_train, y_train):
    """로드된 모델로 추가 학습."""
    # TODO: 필요 없으면 pass
    model.fit(X_train, y_train, epochs=5, verbose=1)
    return model'''
        else:
            return '''def train(model, X_train, y_train):
    # TODO: 학습 또는 패스
    return model'''

    if framework == "sklearn":
        return '''def train(model, X_train, y_train):
    """모델 학습."""
    model.fit(X_train, y_train)
    # 검증 메트릭 로깅
    y_pred = model.predict(X_train)
    acc = accuracy_score(y_train, y_pred)
    mlflow.log_metric("train_accuracy", acc)
    print(f"[AIU] train_accuracy={acc:.4f}")
    return model'''

    elif framework == "pytorch":
        return '''def train(model, X_train, y_train):
    # TODO: PyTorch 학습 루프
    # optimizer = optim.Adam(model.parameters(), lr=0.001)
    # criterion = nn.CrossEntropyLoss()
    raise NotImplementedError'''

    elif framework == "tensorflow":
        return '''def train(model, X_train, y_train):
    """TensorFlow 모델 학습."""
    history = model.fit(X_train, y_train, epochs=10, validation_split=0.2, verbose=1)
    mlflow.log_metric("val_accuracy", history.history.get("val_accuracy", [0])[-1])
    return model'''

    return '''def train(model, X_train, y_train):
    # TODO: 학습 로직
    raise NotImplementedError'''


def gen_section6(framework: str) -> str:
    """섹션 6: 인풋 샘플."""
    if framework in ("sklearn", "tensorflow"):
        return '''def get_input_example(X):
    """MLflow 시그니처용 인풋 샘플."""
    return X[:5]'''
    elif framework == "pytorch":
        return '''def get_input_example(X):
    # TODO: PyTorch 텐서 형태로 반환
    return X[:5]'''
    return '''def get_input_example(X):
    # TODO: 모델 시그니처용 인풋 샘플 반환
    raise NotImplementedError'''


def gen_section7(framework: str) -> str:
    """섹션 7: MLflow 모델 로깅."""
    if framework == "sklearn":
        return '''def log_model(model, input_example):
    """MLflow에 sklearn 모델 로깅."""
    mlflow.sklearn.log_model(
        model,
        artifact_path="model",
        registered_model_name=MODEL_NAME,
        input_example=input_example,
    )'''
    elif framework == "pytorch":
        return '''def log_model(model, input_example):
    # TODO: PyTorch 모델 로깅
    # mlflow.pytorch.log_model(model, "model", registered_model_name=MODEL_NAME)
    raise NotImplementedError'''
    elif framework == "tensorflow":
        return '''def log_model(model, input_example):
    """MLflow에 TensorFlow 모델 로깅."""
    mlflow.tensorflow.log_model(
        model,
        artifact_path="model",
        registered_model_name=MODEL_NAME,
        input_example=input_example,
    )'''
    return '''def log_model(model, input_example):
    # TODO: 프레임워크에 맞는 로깅
    raise NotImplementedError'''


def gen_section8() -> str:
    """섹션 8: config.json."""
    return '''def write_config(save_dir: Path):
    config = {
        "model_name": MODEL_NAME,
        # TODO: 서빙에 필요한 추가 설정
    }
    save_dir.mkdir(parents=True, exist_ok=True)
    (save_dir / "config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
    )'''


def gen_section9(folder_name: str) -> str:
    """섹션 9: 런 스타트."""
    return f'''if __name__ == "__main__":
    USE_DATALAKE = False  # TODO: datalake 사용 여부

    SAVE_DIR = ROOT / "workspace" / "results" / "{folder_name}"

    with mlflow.start_run() as run:
        X_train, y_train = prepare_data()
        model = build_model()
        train(model, X_train, y_train)
        log_model(model, get_input_example(X_train))
        write_config(SAVE_DIR)
        print(f"[AIU] run_id={{run.info.run_id}} model={{MODEL_NAME}} 등록 완료")'''


# ── 메인 ────────────────────────────────────────────────────

def generate(folder_name: str, experiment_name: str, model_name: str):
    folder = MODELS_DIR / folder_name
    if not folder.exists():
        fail(f"폴더를 찾을 수 없습니다: workspace/models/{folder_name}")

    source_dir = folder / "source"
    analysis = analyze_source(source_dir)
    mode = analysis["mode"]
    framework = analysis["framework"]
    files = analysis["files"]

    # 섹션별 생성
    sections = {
        "1": gen_section1(framework, mode, files),
        "2": gen_section2(folder_name, experiment_name, model_name),
        "3": gen_section3(mode, framework, files, source_dir),
        "4": gen_section4(mode, framework, files, source_dir),
        "5": gen_section5(mode, framework),
        "6": gen_section6(framework),
        "7": gen_section7(framework),
        "8": gen_section8(),
        "9": gen_section9(folder_name),
    }

    section_titles = {
        "1": "임포트 영역",
        "2": "MLflow 연동 영역  (작업 환경이 바뀌면 이 부분만 수정)",
        "3": "데이터 준비",
        "4": "모델 준비",
        "5": "트레이닝 펑션",
        "6": "옵션 - 인풋 샘플",
        "7": "MLflow에 모델 로깅",
        "8": "옵션 - config.json 정의",
        "9": "런 스타트",
    }

    # run.py 조합
    lines = [
        f"# =============================================================",
        f"#  AIU run.py - {folder_name}",
        f"#  생성: init 스킬 (모드: {mode}, 프레임워크: {framework})",
        f"# =============================================================",
        "",
    ]
    for no, title in section_titles.items():
        lines += [
            f"# {'-'*61}",
            f"# {no}. {title}",
            f"# {'-'*61}",
            sections[no],
            "",
            "",
        ]

    run_py = folder / "run.py"
    run_py.write_text("\n".join(lines), encoding="utf-8")

    # TODO 항목 추출
    todo_items = []
    for i, line in enumerate(lines, 1):
        if "# TODO" in line:
            todo_items.append(f"  line {i}: {line.strip()}")

    # 상태 저장
    set_state(folder,
        status="initialized",
        last_action="init",
        mode=mode,
        framework=framework,
        experiment_name=experiment_name,
        model_name=model_name,
    )
    set_current_folder(folder_name)

    ok({
        "folder": folder_name,
        "mode": mode,
        "framework": framework,
        "run_py": str(run_py),
        "todo_count": len(todo_items),
        "todo_items": todo_items,
        "analysis": analysis,
        "message": (
            f"✓ run.py 생성 완료: workspace/models/{folder_name}/run.py\n"
            f"  모드: {mode} / 프레임워크: {framework}\n"
            f"  분석: {analysis['reason']}\n"
            + (f"\n  ⚠ TODO 항목 {len(todo_items)}개 — validate 후 안내받으세요."
               if todo_items else "\n  ✓ TODO 항목 없음 — validate 실행 권장")
        )
    })


if __name__ == "__main__":
    if len(sys.argv) < 4:
        fail("사용법: generate_run.py <폴더명> <실험명> <모델명>")
    generate(sys.argv[1], sys.argv[2], sys.argv[3])
