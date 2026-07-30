import mlflow
import json

class LangflowExportedModel(mlflow.pyfunc.PythonModel):
    def load_context(self, context):
        from langflow.load import load_flow_from_json
        # artifact로 함께 저장된 flow.json 사용
        flow_path = context.artifacts["flow_json"]
        self.flow = load_flow_from_json(flow_path, disable_logs=True)

    def predict(self, context, model_input, params=None):
        query = model_input["input"][0]
        result = self.flow(query)
        return result

with mlflow.start_run():
    mlflow.pyfunc.log_model(
        artifact_path="langflow_pipeline",
        python_model=LangflowExportedModel(),
        artifacts={"flow_json": "flow.json"},   # export한 파일 경로
        pip_requirements=["langflow==<버전고정>"],
        registered_model_name="langflow-pipeline-v1"
    )
