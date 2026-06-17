"""
skills/deploy/scripts/deploy_run.py

배포 진입점.
- 게이트: predicted 상태여야 배포 가능
- config.json(aistudio) + 상태(.aiu_state.json)에서 정보 수집
- deploy_client.deploy_model() 호출 → Endpoint URL을 상태에 저장

사용:
    python skills/deploy/scripts/deploy_run.py [폴더명]
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from skills.common import (
    safe_main,
    ok, fail, progress, get_current_folder, get_state, set_state,
    check_gate, check_files_consistency, get_aistudio_config, MODELS_DIR
)

# 같은 폴더의 deploy_client
sys.path.insert(0, str(Path(__file__).resolve().parent))


def get_folder(name=None):
    try:
        if name:
            f = MODELS_DIR / name
            if not f.exists():
                fail(f"폴더 없음: workspace/models/{name}")
            return f
        f = get_current_folder()
        if not f:
            fail("현재 작업 폴더가 없습니다.")
        return f
    except SystemExit:
        raise
    except Exception as e:
        fail(f"폴더 확인 오류: {e}")


def load_dependencies(folder: Path) -> list:
    """requirements.txt 내용을 리스트로 로드."""
    candidates = [
        folder / "requirements.txt",
        folder / "source" / "requirements.txt",
    ]
    for p in candidates:
        if p.exists():
            lines = [l.strip() for l in p.read_text(encoding="utf-8").splitlines()]
            return [l for l in lines if l and not l.startswith("#")]
    return []  # 없으면 빈 리스트 (선택)


def run_deploy(folder: Path):
    # 게이트: predicted 필요
    fc = check_files_consistency(folder)
    if not fc["ok"]:
        fail(fc["message"])
    passed, msg = check_gate(folder, "deploy")
    if not passed:
        fail(msg)

    state = get_state(folder)
    model_nm  = state.get("model_name")
    model_ver = state.get("model_version", "latest")  # 없으면 latest

    if not model_nm:
        fail("등록된 모델명이 없습니다. 먼저 학습(train)을 실행하세요.")

    # AI Studio 설정 확인
    cfg = get_aistudio_config()
    api_url    = cfg.get("api_url", "")
    project_id = cfg.get("project_id", "")
    system_key = cfg.get("system_key", "")

    if not api_url or not project_id:
        fail(
            "AI Studio 배포 설정이 없습니다.\n"
            "config.json 의 aistudio 섹션에 api_url, project_id 를 설정하세요.\n"
            "(config.sample.json 참고)"
        )

    # 의존성 로드
    dependencies = load_dependencies(folder)

    # 배포 실행
    try:
        from deploy_client import AIStudioAPIClient, APIConfig, deploy_model
    except ImportError as e:
        fail(f"deploy_client 로드 실패: {e}")

    try:
        api_cfg = APIConfig(api_url=api_url, system_key=system_key, project_id=project_id)
        client  = AIStudioAPIClient(api_cfg)

        progress(f"배포 시작: project={project_id}, model={model_nm} v{model_ver}")

        result = deploy_model(
            client,
            project_id=project_id,
            model_nm=model_nm,
            model_ver=model_ver,
            dependencies=dependencies,
            on_progress=lambda m: progress(m),
        )
    except SystemExit:
        raise
    except Exception as e:
        fail(
            f"배포 실패: {e}\n"
            "AI Studio API 설정(api_url, project_id, system_key)과\n"
            "deploy_client.py 의 API 경로/응답 필드(TODO)를 확인하세요."
        )

    # Endpoint URL 상태에 저장 (predict ②에서 사용)
    set_state(folder,
        status="deployed",
        last_action="deploy",
        endpoint_id=result["endpoint_id"],
        endpoint_url=result["endpoint_url"],
    )

    ok({
        "project_id":   project_id,
        "model_name":   model_nm,
        "model_version": model_ver,
        "endpoint_id":  result["endpoint_id"],
        "endpoint_url": result["endpoint_url"],
        "message": (
            f"✓ 배포 완료\n"
            f"  프로젝트   : {project_id}\n"
            f"  모델       : {model_nm} v{model_ver}\n"
            f"  Endpoint   : {result['endpoint_url']}\n"
            f"  → Endpoint 추론 테스트: '엔드포인트 추론 테스트해줘'"
        )
    })


def _main():
    folder_name = sys.argv[1] if len(sys.argv) > 1 else None
    run_deploy(get_folder(folder_name))


if __name__ == "__main__":
    safe_main(_main)
