"""
_bootstrap.py - install.bat/sh 에서 호출하는 부트스트랩 스크립트
rich, ruamel.yaml 등 초기 패키지를 조용히 설치한다.
cmd의 따옴표 파싱 문제를 우회하기 위해 별도 파일로 분리.
"""
import subprocess
import sys
import os

packages = ["rich"]

extra = []
nexus = os.environ.get("PIP_INDEX_URL", "")
if nexus:
    nexus_host = nexus.split("/")[2] if "/" in nexus else nexus
    extra = ["--index-url", nexus, "--trusted-host", nexus_host]

result = subprocess.run(
    [sys.executable, "-m", "pip", "install"] + packages + extra +
    ["--quiet", "--no-input", "--disable-pip-version-check"],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)

# returncode 1 = 이미 설치됨 등 무해한 경우 포함
sys.exit(0 if result.returncode in (0, 1) else result.returncode)
