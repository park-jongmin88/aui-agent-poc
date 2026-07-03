import argparse
import ast
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from urllib.parse import urlparse


def resolve_workspace_project(raw_project: str) -> Path:
    raw = raw_project.strip()
    if raw in {"<workspace-root>", "<current-project-folder>", "<model-project-folder>"}:
        raw = "."
    elif "<" in raw or ">" in raw:
        raise ValueError("replace placeholder project path before running, for example: --project .")

    project = Path(raw).expanduser().resolve()
    parts = project.parts
    if ".opencode" in parts:
        opencode_index = parts.index(".opencode")
        if opencode_index > 0:
            return Path(*parts[:opencode_index]).resolve()
    return project


@dataclass
class InferenceReport:
    project_path: str
    input_example_path: str | None
    inferencetest_path: str | None
    req_url: str | None
    req_url_status: str
    result_path: str | None
    executed: bool
    status_code: int | None = None
    response_schema: str | None = None
    failures: list[str] = field(default_factory=list)
    output_preview: str | None = None


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def find_input_example(project: Path) -> Path | None:
    for name in ["input_example.json", "sample_input.json", "example.json"]:
        candidate = project / name
        if candidate.exists():
            return candidate
    return None


def find_inferencetest(project: Path) -> Path | None:
    candidate = project / "inferencetest.py"
    return candidate if candidate.is_file() else None


def literal_assignment(path: Path, name: str) -> str | None:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
    except SyntaxError:
        return None
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            continue
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            return node.value.value
    return None


def validate_predict_url(url: str | None) -> tuple[str | None, str, str | None]:
    value = (url or "").strip()
    if not value:
        return None, "missing", "missing_req_url"
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return value, "invalid", "invalid_req_url_scheme"
    if not value.rstrip("/").endswith(":predict"):
        return value, "invalid", "req_url_must_end_with_predict"
    return value, "set", None


def preview(value) -> str:
    text = json.dumps(value, ensure_ascii=False, default=str)
    return text[:1000]


def response_schema(value) -> str:
    if isinstance(value, dict):
        return "object:" + ",".join(sorted(str(key) for key in value.keys())[:10])
    if isinstance(value, list):
        return f"array:{len(value)}"
    return type(value).__name__


def post_remote_predict(req_url: str, payload):
    import requests

    message = json.dumps(payload)
    headers = {"Content-Type": "application/json"}
    response = requests.post(req_url, headers=headers, data=message)
    try:
        body = response.json()
    except ValueError:
        body = {"text": response.text}
    return response.status_code, body


def main():
    parser = argparse.ArgumentParser(description="Step 6: post input_example.json to a remote :predict URL.")
    parser.add_argument("--project", default=".", help="selected model work folder")
    parser.add_argument("--url", help="remote inference URL ending with :predict")
    parser.add_argument("--input-example", help="explicit input example JSON path")
    parser.add_argument("--execute", action="store_true", help="actually send HTTP POST to the remote :predict URL")
    parser.add_argument("--output", help="optional result JSON file path; no result file is written unless this is set")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    args = parser.parse_args()

    project = resolve_workspace_project(args.project)
    input_path = Path(args.input_example).expanduser().resolve() if args.input_example else find_input_example(project)
    inferencetest_path = find_inferencetest(project)
    req_url_from_file = literal_assignment(inferencetest_path, "req_url") if inferencetest_path else None
    req_url, req_url_status, req_url_failure = validate_predict_url(args.url or req_url_from_file)

    failures: list[str] = []
    if input_path is None:
        failures.append("missing_input_example")
    if inferencetest_path is None:
        failures.append("missing_inferencetest_py")
    if req_url_failure:
        failures.append(req_url_failure)

    payload = None
    if input_path is not None:
        try:
            payload = load_json(input_path)
        except Exception as exc:
            failures.append(f"schema_error:{exc}")

    status_code = None
    output = None
    schema = None
    if args.execute and not failures and req_url is not None:
        try:
            status_code, output = post_remote_predict(req_url, payload)
            schema = response_schema(output)
            if status_code >= 400:
                failures.append(f"http_error:{status_code}")
        except Exception as exc:
            failures.append(f"remote_predict_error:{exc}")

    output_path = Path(args.output).expanduser().resolve() if args.output else None
    result_path = str(output_path) if output_path else None
    report = InferenceReport(
        project_path=str(project),
        input_example_path=str(input_path) if input_path else None,
        inferencetest_path=str(inferencetest_path) if inferencetest_path else None,
        req_url=req_url,
        req_url_status=req_url_status,
        result_path=result_path,
        executed=args.execute,
        status_code=status_code,
        response_schema=schema,
        failures=failures,
        output_preview=preview(output) if output is not None else None,
    )
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(asdict(report), ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    if args.json:
        print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
    else:
        print("Project: .")
        print(f"Input example: {report.input_example_path or 'missing'}")
        print(f"Inference entrypoint: {report.inferencetest_path or 'missing'}")
        print(f"req_url status: {report.req_url_status}")
        print(f"Result path: {report.result_path or 'not written'}")
        print(f"Executed: {report.executed}")
        print(f"Status code: {report.status_code if report.status_code is not None else 'none'}")
        print(f"Response schema: {report.response_schema or 'none'}")
        if report.output_preview:
            print(f"Output preview: {report.output_preview}")
        if report.failures:
            print("Failures:")
            for failure in report.failures:
                print(f"- {failure}")
            if "missing_req_url" in report.failures or "req_url_must_end_with_predict" in report.failures:
                print("조치: inferencetest.py의 req_url 또는 --url에 원격 :predict URL을 입력하세요.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[error] {exc}", file=sys.stderr)
        sys.exit(1)
