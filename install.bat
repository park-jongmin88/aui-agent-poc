@echo off
title aiu-agent Install

REM ====================================================
REM  [운영자 설정] 사내 넥서스 PyPI 주소 (비우면 기본 pip)
REM  예) set NEXUS_PYPI=http://nexus.company.com/repository/pypi-proxy/simple
REM      set NEXUS_HOST=nexus.company.com
REM ====================================================
set NEXUS_PYPI=
set NEXUS_HOST=

echo [aiu-agent] 준비 중입니다. 잠시만 기다려주세요...
echo.

python --version > nul 2>&1
if errorlevel 1 (
    echo Python 3.10 이상을 먼저 설치하세요.
    pause
    exit /b 1
)

if not exist .venv (
    echo [aiu-agent] 가상환경 생성 중...
    python -m venv --without-pip .venv
    .venv\Scripts\python.exe -m ensurepip --default-pip
)

set PIP_OPTS=
if not "%NEXUS_PYPI%"=="" set PIP_OPTS=--index-url %NEXUS_PYPI% --trusted-host %NEXUS_HOST%
if not "%NEXUS_PYPI%"=="" set PIP_INDEX_URL=%NEXUS_PYPI%

.venv\Scripts\python.exe main.py --setup
if errorlevel 1 (
    echo.
    echo   +=== 설치 중 문제가 발생했습니다 ===================+
    echo   ^| 위 메시지에서 원인을 확인하세요.
    echo   ^|
    echo   ^| 주요 원인:
    echo   ^|   - LLM 연결 실패: config.json 의 base_url/api_key/type 확인
    echo   ^|   - 의존성 설치 실패: 네트워크 또는 넥서스 설정 확인
    echo   ^|   - 설정 누락: config.json 의 TODO 항목 미입력
    echo   ^|
    echo   ^| 수정 후 start.bat 으로 재실행하세요.
    echo   +====================================================+
    pause
    exit /b 1
)
echo.
echo 다음부터는 start.bat 으로 바로 실행할 수 있습니다.
echo.
echo ML 작업(학습/추론)을 위해 추가 설치가 필요합니다:
echo   .venv\Scripts\python -m pip install -r setting\requirements-ml.txt
pause
