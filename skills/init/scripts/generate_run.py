"""
skills/init/scripts/generate_run.py

workspace/models/<folder>/source/ 를 분석해
workspace/models/<folder>/run.py 와 model_wrapper.py 를 자동 생성한다.

모든 모델은 pyfunc + ModelWrapper 로 MLflow에 등록된다 (사내 표준).
모드는 데이터/모델 준비 방식의 차이만 의미한다:
  LOAD_MODEL  — pkl/pt/h5 모델 파일 있음
  RUN_CODE    — .py 코드 파일 있음
  DATA_ONLY   — csv 등 데이터 파일만 있음
  TEMPLATE    — 빈 폴더

사용:
    python skills/init/scripts/generate_run.py <폴더명> <실험명> <모델명>
"""
import sys
import re
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from skills.common import (
    safe_main,
    ok, fail, MODELS_DIR, TEMPLATES_DIR, CONFIG_PATH,
    get_mlflow_config, get_state, set_state, set_current_folder, list_model_folders
)


# ── ModelWrapper 템플릿 (모델 폴더에 같이 생성) ──────────────
MODEL_WRAPPER_TEMPLATE = '''"""
model_wrapper.py — pyfunc ModelWrapper (AI Studio 서빙용)

MLflow pyfunc 으로 모델을 등록/서빙하기 위한 래퍼.
run.py 의 log_model 에서 code_paths 로 이 파일을 동봉한다.

predict 반환 형식 (aiu_dict):
  aiu_output     : 모델 추론 결과
  aiu_monitoring : AI Studio 대시보드 모니터링 값
                   (int/float 또는 int/float 리스트만 허용,
                    문자열/딕셔너리/불리언 섞인 리스트는 불가)
"""
import json
import joblib
import numpy as np
import mlflow.pyfunc


class ModelWrapper(mlflow.pyfunc.PythonModel):
    """학습된 모델을 감싸 AI Studio 서빙 인터페이스를 표준화한다."""

    def __init__(self):
        self.model = None
        self.config = None

    def load_context(self, context):
        """서빙 환경에서 모델/설정을 로드한다."""
        model_path = context.artifacts["model"].replace("\\\\", "/")
        self.model = joblib.load(model_path)

        config_path = context.artifacts["config"].replace("\\\\", "/")
        with open(config_path, "r") as f:
            self.config = json.load(f)

    def predict(self, context, payload):
        """추론 실행.

        payload (AI Studio 서빙 환경이 주입):
          trace_id : 추적 ID
          pis_name : 서비스명
          logger   : 로거 (콜러블)
          input    : [{"data": ...}] 추론 데이터
        """
        try:
            trace_id   = payload["trace_id"]
            extra_json = {"trace_id": trace_id}
            pis_name   = payload["pis_name"]
            logger     = payload["logger"]()
            input_data = payload["input"][0]

            # TODO: inference 과정을 데이터/모델에 맞게 수정
            model_input = input_data["data"]
            predictions = self.model.predict(model_input)
            predictions_rounded = np.round(predictions, 2)

            # AI Studio 모니터링 반환
            aiu_dict = dict()
            aiu_dict["aiu_output"]     = predictions_rounded.tolist()
            # TODO: 모니터링 값은 int/float 또는 그 리스트만 가능
            aiu_dict["aiu_monitoring"] = predictions_rounded.tolist()

            return aiu_dict

        except Exception as e:
            logger.error(str(e), extra=extra_json)
            raise
'''

MODEL_EXTENSIONS = {
    "sklearn":    [".pkl", ".joblib"],
    "pytorch":    [".pt", ".pth"],
    "tensorflow": [".h5", ".keras", ".pb"],
}
DATA_EXTENSIONS = [".csv", ".parquet", ".xlsx", ".json", ".npy", ".npz"]
CODE_EXTENSIONS = [".py", ".ipynb"]


def analyze_source(source_dir: Path) -> dict:
    """source/ 폴더 분석 → 모드/프레임워크 판별."""
    if not source_dir.exists():
        return {"mode": "TEMPLATE", "framework": "sklearn", "files": {}, "reason": "빈 폴더"}

    files = {"model": [], "data": [], "code": [], "other": []}
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
    code_parts = []
    for f in source_dir.iterdir():
        if f.suffix == ".py" and f.is_file():
            code_parts.append(f"# === {f.name} ===\n" + f.read_text(encoding="utf-8", errors="replace"))
    return "\n\n".join(code_parts)


# ── 섹션별 코드 생성 ────────────────────────────────────────

def gen_section1(framework: str, mode: str, source_files: dict) -> str:
    """섹션 1: 임포트."""
    imports = ["import os", "import json", "import numpy as np", "from pathlib import Path", "", "import mlflow"]

    if mode == "PYFUNC":
        imports += [
            "import mlflow.pyfunc",
            "",
            "import joblib",
            "import pandas as pd",
            "",
            "from sklearn.model_selection import train_test_split",
            "from sklearn.metrics import accuracy_score, mean_squared_error",
            "from sklearn.ensemble import RandomForestClassifier  # TODO: 사용할 모델로 변경",
            "",
            "# ModelWrapper (같은 폴더의 model_wrapper.py)",
            "from model_wrapper import ModelWrapper",
        ]
    elif framework == "sklearn":
        imports += [
            "import mlflow.sklearn",
            "",
            "from sklearn.ensemble import RandomForestClassifier  # TODO: 사용할 모델로 변경",
            "from sklearn.model_selection import train_test_split",
            "from sklearn.metrics import accuracy_score",
            "import joblib",
        ]
        if any(f.endswith(".csv") for f in source_files.get("data", [])):
            imports.append("import pandas as pd")
    elif framework == "pytorch":
        imports += ["", "import torch", "import torch.nn as nn", "import torch.optim as optim"]
    elif framework == "tensorflow":
        imports += ["", "import tensorflow as tf"]
    elif framework == "custom":
        imports += ["", "# TODO: source/ 코드에서 필요한 임포트 추가"]

    return "\n".join(imports)


def gen_section2(folder_name: str, experiment_name: str, model_name: str) -> str:
    """섹션 2: MLflow 연동."""
    mlflow_cfg = get_mlflow_config()
    uri      = mlflow_cfg.get("tracking_uri", "")
    username = mlflow_cfg.get("username", "")
    password = mlflow_cfg.get("password", "")

    uri_line = f'MLFLOW_TRACKING_URI = "{uri}"' if uri else 'MLFLOW_TRACKING_URI = ""  # TODO: MLflow 서버 주소'

    return f'''ROOT = Path(__file__).resolve().parents[2]

{uri_line}
MLFLOW_USERNAME = "{username}"
MLFLOW_PASSWORD = "{password}"

# TLS 인증서 검증 비활성화 (사내 자체 서명 인증서 환경)
os.environ["MLFLOW_TRACKING_INSECURE_TLS"] = "true"

mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
if MLFLOW_USERNAME:
    os.environ["MLFLOW_TRACKING_USERNAME"] = MLFLOW_USERNAME
    os.environ["MLFLOW_TRACKING_PASSWORD"] = MLFLOW_PASSWORD

EXPERIMENT_NAME = "{experiment_name}"
MODEL_NAME      = "{model_name}"

mlflow.set_experiment(EXPERIMENT_NAME)'''


def gen_section3(mode: str, framework: str, source_files: dict, source_dir: Path) -> str:
    """섹션 3: 데이터 준비."""
    data_files = source_files.get("data", [])

    if mode == "PYFUNC":
        csv_files = [f for f in data_files if f.endswith(".csv")]
        if csv_files:
            fname = csv_files[0]
            return f'''def prepare_data():
    """데이터 로드 및 train/test 분리."""
    data_path = Path(__file__).resolve().parent / "source" / "{fname}"
    df = pd.read_csv(data_path)
    target_col = df.columns[-1]  # TODO: 실제 타겟 컬럼명으로 변경
    X = df.drop(columns=[target_col])
    y = df[target_col]
    return train_test_split(X, y, test_size=0.2, random_state=42)'''
        return '''def prepare_data():
    """데이터 로드."""
    # TODO: 데이터 로드 구현
    # 예) df = pd.read_csv(Path(__file__).resolve().parent / "source" / "data.csv")
    raise NotImplementedError'''

    if mode == "LOAD_MODEL":
        if framework == "sklearn":
            return '''def prepare_data():
    """샘플 데이터 생성 (모델 검증용)."""
    from sklearn.datasets import make_classification
    X, y = make_classification(n_samples=100, n_features=10, random_state=42)
    return train_test_split(X, y, test_size=0.2, random_state=42)'''
        return '''def prepare_data():
    # TODO: 검증용 샘플 데이터 준비
    raise NotImplementedError'''

    if data_files:
        csv_files = [f for f in data_files if f.endswith(".csv")]
        if csv_files and framework == "sklearn":
            fname = csv_files[0]
            return f'''def prepare_data():
    """source/ 의 데이터 파일 로드."""
    data_path = Path(__file__).resolve().parent / "source" / "{fname}"
    df = pd.read_csv(data_path)
    target_col = df.columns[-1]  # TODO: 타겟 컬럼명 확인
    X = df.drop(columns=[target_col]).values
    y = df[target_col].values
    return train_test_split(X, y, test_size=0.2, random_state=42)'''

    return '''def prepare_data():
    # TODO: 데이터 로딩/생성
    raise NotImplementedError'''


def gen_section4(mode: str, framework: str, source_files: dict, source_dir: Path) -> str:
    """섹션 4: 모델 준비."""
    model_files = source_files.get("model", [])

    if mode == "PYFUNC":
        if model_files:
            mfile = model_files[0]
            return f'''def build_model():
    """저장된 모델 로드."""
    model_path = Path(__file__).resolve().parent / "source" / "{mfile}"
    return joblib.load(model_path)'''
        return '''def build_model():
    """모델 정의 또는 로드."""
    # TODO: 모델 정의
    # 예) from sklearn.linear_model import ElasticNet
    #     return ElasticNet(alpha=0.001, l1_ratio=0.5, random_state=42)
    raise NotImplementedError'''

    if mode == "LOAD_MODEL" and model_files:
        mfile = model_files[0]
        mpath = f'Path(__file__).resolve().parent / "source" / "{mfile}"'
        if framework == "sklearn":
            return f'''def build_model():
    return joblib.load({mpath})'''
        elif framework == "pytorch":
            return f'''def build_model():
    # TODO: 모델 클래스 정의 후 활성화
    raise NotImplementedError'''
        elif framework == "tensorflow":
            return f'''def build_model():
    return tf.keras.models.load_model(str({mpath}))'''

    if mode == "RUN_CODE":
        code = read_source_code(source_dir)
        train_funcs = re.findall(r'def\s+(train\w*|fit\w*|run\w*)\s*\(', code)
        hint = f"# 발견된 함수: {train_funcs}" if train_funcs else ""
        return f'''def build_model():
    {hint}
    # TODO: source/ 코드에서 모델 로드 또는 정의
    raise NotImplementedError'''

    if framework == "sklearn":
        return '''def build_model():
    # TODO: 사용할 모델로 변경
    return RandomForestClassifier(n_estimators=100, random_state=42)'''
    return '''def build_model():
    # TODO: 모델 정의
    raise NotImplementedError'''


def gen_section5(mode: str, framework: str) -> str:
    """섹션 5: 트레이닝."""
    if mode == "PYFUNC":
        return '''def train(model, X_train, y_train):
    """모델 학습 및 메트릭 로깅."""
    model.fit(X_train, y_train)
    y_pred = model.predict(X_train)
    # TODO: 문제 유형에 맞는 메트릭으로 변경
    # 분류: accuracy_score(y_train, y_pred)
    # 회귀: mean_squared_error(y_train, y_pred)
    mlflow.log_metric("train_accuracy", accuracy_score(y_train, y_pred))
    print(f"[AIU] train_accuracy={accuracy_score(y_train, y_pred):.4f}")
    return model'''

    if mode == "LOAD_MODEL":
        if framework == "sklearn":
            return '''def train(model, X_train, y_train):
    # TODO: 재학습 필요 없으면 pass
    model.fit(X_train, y_train)
    return model'''
        return '''def train(model, X_train, y_train):
    return model'''

    if framework == "sklearn":
        return '''def train(model, X_train, y_train):
    model.fit(X_train, y_train)
    acc = accuracy_score(y_train, model.predict(X_train))
    mlflow.log_metric("train_accuracy", acc)
    print(f"[AIU] train_accuracy={acc:.4f}")
    return model'''
    elif framework == "pytorch":
        return '''def train(model, X_train, y_train):
    # TODO: PyTorch 학습 루프
    raise NotImplementedError'''
    elif framework == "tensorflow":
        return '''def train(model, X_train, y_train):
    history = model.fit(X_train, y_train, epochs=10, validation_split=0.2, verbose=1)
    mlflow.log_metric("val_accuracy", history.history.get("val_accuracy", [0])[-1])
    return model'''
    return '''def train(model, X_train, y_train):
    # TODO: 학습 로직
    raise NotImplementedError'''


def gen_section6(mode: str, framework: str) -> str:
    """섹션 6: 인풋 샘플."""
    if mode == "PYFUNC":
        return '''def get_input_example(X_test, batch_size=10):
    """KServe 형식의 input_example 생성 및 JSON 저장."""
    sample = X_test.head(batch_size).to_numpy() if hasattr(X_test, "head") else X_test[:batch_size]

    input_example = {
        "input": [
            {
                "name": MODEL_NAME,
                "shape": list(sample.shape),
                "datatype": type(sample).__name__,
                "data": sample.tolist(),
            }
        ]
    }

    # input_example.json 저장 (추론 테스트 재사용)
    with open("input_example.json", "w", encoding="utf-8") as f:
        json.dump(input_example, f, indent=2)
    print("[AIU] input_example.json 저장 완료")

    return input_example'''

    if framework in ("sklearn", "tensorflow"):
        return '''def get_input_example(X):
    return X[:5]'''
    elif framework == "pytorch":
        return '''def get_input_example(X):
    # TODO: PyTorch 텐서 형태로 반환
    return X[:5]'''
    return '''def get_input_example(X):
    # TODO: 인풋 샘플 반환
    raise NotImplementedError'''


def gen_section7(mode: str, framework: str) -> str:
    """섹션 7: MLflow 모델 로깅."""
    if mode == "PYFUNC":
        return '''def log_model(model, input_example, save_dir: Path):
    """pyfunc + ModelWrapper 로 MLflow에 등록."""
    # 모델 파일 저장 (artifacts로 등록)
    save_dir.mkdir(parents=True, exist_ok=True)
    model_path = str(save_dir / "model.pkl").replace("\\\\", "/")
    joblib.dump(model, model_path)

    # config 저장
    config_dir = save_dir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = str(config_dir / "config.json").replace("\\\\", "/")
    # TODO: 저장할 config 내용 추가
    with open(config_path, "w") as f:
        json.dump({"model_name": MODEL_NAME}, f, indent=2)

    mlflow.pyfunc.log_model(
        python_model=ModelWrapper(),
        artifact_path="model",
        code_paths=["model_wrapper.py"],     # ModelWrapper 동봉 (같은 폴더)
        artifacts={
            "model":  model_path,
            "config": config_path,
        },
        input_example=input_example,
        registered_model_name=MODEL_NAME,
    )'''

    if framework == "sklearn":
        return '''def log_model(model, input_example):
    mlflow.sklearn.log_model(
        model,
        artifact_path="model",
        registered_model_name=MODEL_NAME,
        input_example=input_example,
    )'''
    elif framework == "pytorch":
        return '''def log_model(model, input_example):
    # TODO: PyTorch 모델 로깅
    raise NotImplementedError'''
    elif framework == "tensorflow":
        return '''def log_model(model, input_example):
    mlflow.tensorflow.log_model(
        model,
        artifact_path="model",
        registered_model_name=MODEL_NAME,
        input_example=input_example,
    )'''
    return '''def log_model(model, input_example):
    # TODO: 프레임워크에 맞는 로깅
    raise NotImplementedError'''


def gen_section8(mode: str) -> str:
    """섹션 8: Dataset 로깅 + config."""
    if mode == "PYFUNC":
        return '''def log_datasets(train_df, test_df):
    """MLflow Dataset 추적 (MLflow 3.x 권장)."""
    # TODO: 타겟 컬럼명 확인
    target_col = "target"
    mlflow_train_ds = mlflow.data.from_pandas(train_df, name="Train", targets=target_col)
    mlflow_test_ds  = mlflow.data.from_pandas(test_df,  name="Test",  targets=target_col)
    mlflow.log_input(mlflow_train_ds, context="training")
    mlflow.log_input(mlflow_test_ds,  context="test")'''

    return '''def write_config(save_dir: Path):
    config = {
        "model_name": MODEL_NAME,
        # TODO: 서빙에 필요한 추가 설정
    }
    save_dir.mkdir(parents=True, exist_ok=True)
    (save_dir / "config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
    )'''


def gen_section9(folder_name: str, framework: str, mode: str) -> str:
    """섹션 9: 런 스타트."""
    if mode == "PYFUNC":
        return f'''if __name__ == "__main__":
    SAVE_DIR = ROOT / "workspace" / "results" / "{folder_name}"

    with mlflow.start_run() as run:
        X_train, X_test, y_train, y_test = prepare_data()

        # Dataset 로깅
        import pandas as pd
        train_df = pd.concat([X_train, y_train], axis=1) if hasattr(X_train, "columns") else None
        test_df  = pd.concat([X_test,  y_test],  axis=1) if hasattr(X_test,  "columns") else None
        if train_df is not None:
            log_datasets(train_df, test_df)

        # 하이퍼파라미터 로깅
        params = {{
            # TODO: 사용한 하이퍼파라미터 추가
            # "alpha": 0.001, "l1_ratio": 0.5,
        }}
        mlflow.log_params(params)

        # 학습
        model = build_model()
        train(model, X_train, y_train)

        # 평가 메트릭
        y_pred = model.predict(X_test)
        # TODO: 문제 유형에 맞는 메트릭으로 변경
        test_acc = accuracy_score(y_test, y_pred)
        mlflow.log_metric("test_accuracy", test_acc)
        print(f"[AIU] test_accuracy={{test_acc:.4f}}")

        # input_example 생성 (KServe 형식)
        input_example = get_input_example(X_test)

        # 모델 등록 (pyfunc + ModelWrapper)
        log_model(model, input_example, SAVE_DIR)

        print(f"[AIU] run_id={{run.info.run_id}} model={{MODEL_NAME}} 등록 완료")
        print(f"[AIU] input_example.json 위치: {{Path('input_example.json').resolve()}}")'''

    eval_block = ""
    if framework == "sklearn":
        eval_block = '''
        from sklearn.metrics import accuracy_score
        test_acc = accuracy_score(y_test, model.predict(X_test))
        mlflow.log_metric("test_accuracy", test_acc)
        print(f"[AIU] test_accuracy={test_acc:.4f}")'''

    return f'''if __name__ == "__main__":
    USE_DATALAKE = False  # TODO: datalake 사용 여부

    SAVE_DIR = ROOT / "workspace" / "results" / "{folder_name}"

    with mlflow.start_run() as run:
        X_train, X_test, y_train, y_test = prepare_data()
        model = build_model()
        train(model, X_train, y_train){eval_block}
        log_model(model, get_input_example(X_train))
        write_config(SAVE_DIR)
        print(f"[AIU] run_id={{run.info.run_id}} model={{MODEL_NAME}} 등록 완료")'''


# ── 메인 ────────────────────────────────────────────────────

def generate(folder_name: str, experiment_name: str, model_name: str):
    folder = MODELS_DIR / folder_name
    if not folder.exists():
        fail(f"폴더를 찾을 수 없습니다: workspace/models/{folder_name}")

    source_dir = folder / "source"
    analysis   = analyze_source(source_dir)
    mode       = analysis["mode"]      # 데이터/모델 준비 방식 (LOAD_MODEL/DATA_ONLY/RUN_CODE/TEMPLATE)
    framework  = analysis["framework"]
    files      = analysis["files"]

    # 모든 모델은 pyfunc + ModelWrapper 로 등록한다 (사내 표준).
    # mode 는 데이터/모델 준비(섹션 3,4) 방식만 결정하고,
    # 등록 관련 섹션(1,6,7,8,9)은 항상 PYFUNC 로 생성한다.
    REG = "PYFUNC"  # 등록 방식 고정

    sections = {
        "1": gen_section1(framework, REG, files),
        "2": gen_section2(folder_name, experiment_name, model_name),
        "3": gen_section3(mode, framework, files, source_dir),
        "4": gen_section4(mode, framework, files, source_dir),
        "5": gen_section5(REG, framework),
        "6": gen_section6(REG, framework),
        "7": gen_section7(REG, framework),
        "8": gen_section8(REG),
        "9": gen_section9(folder_name, framework, REG),
    }

    section_titles = {
        "1": "임포트 영역",
        "2": "MLflow 연동 영역  (작업 환경이 바뀌면 이 부분만 수정)",
        "3": "데이터 준비",
        "4": "모델 준비",
        "5": "트레이닝 펑션",
        "6": "인풋 샘플 (KServe 형식 input_example.json 생성)",
        "7": "MLflow 모델 로깅 (pyfunc + ModelWrapper)",
        "8": "Dataset 로깅",
        "9": "런 스타트",
    }

    lines = [
        "# =============================================================",
        f"#  AIU run.py - {folder_name}",
        f"#  생성: init 스킬 (모드: {mode}, 프레임워크: {framework})",
        "# =============================================================",
        "",
    ]
    for no, title in section_titles.items():
        lines += [
            f"# {'-'*61}",
            f"# {no}. {title}",
            f"# {'-'*61}",
            sections[no],
            "",
        ]

    run_py_path = folder / "run.py"
    run_py_path.write_text("\n".join(lines), encoding="utf-8")

    # model_wrapper.py 생성 (이미 있으면 사용자 것 유지)
    wrapper_path = folder / "model_wrapper.py"
    wrapper_created = False
    if not wrapper_path.exists():
        wrapper_path.write_text(MODEL_WRAPPER_TEMPLATE, encoding="utf-8")
        wrapper_created = True

    # TODO 개수
    content = "\n".join(lines)
    todo_items = re.findall(r'# TODO:.*', content)

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
        "folder":     folder_name,
        "mode":       mode,
        "framework":  framework,
        "run_py":     str(run_py_path),
        "model_wrapper": str(wrapper_path),
        "wrapper_created": wrapper_created,
        "todo_count": len(todo_items),
        "todo_items": todo_items,
        "message": (
            f"✓ run.py 생성 완료: workspace/models/{folder_name}/run.py\n"
            + (f"✓ model_wrapper.py 생성 (pyfunc 등록용)\n" if wrapper_created
               else f"  model_wrapper.py 기존 파일 유지\n")
            + f"  모드: {mode} / 프레임워크: {framework} / 등록: pyfunc+ModelWrapper\n"
            + (f"  TODO {len(todo_items)}개 — '검증해줘'로 확인하세요." if todo_items else "")
        )
    })


def _main():
    if len(sys.argv) < 4:
        fail("사용법: generate_run.py <폴더명> <실험명> <모델명>")
    generate(sys.argv[1], sys.argv[2], sys.argv[3])


if __name__ == "__main__":
    safe_main(_main)
