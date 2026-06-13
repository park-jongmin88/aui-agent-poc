@echo off
title aiu-agent Quick Start

REM ====================================================
REM  [운영자 설정] 사내 넥서스 PyPI 주소 (비우면 기본 pip)
REM  예) set NEXUS_PYPI=http://nexus.company.com/repository/pypi-proxy/simple
REM      set NEXUS_HOST=nexus.company.com
REM ====================================================
set NEXUS_PYPI=
set NEXUS_HOST=

echo aiu-agent 준비 중입니다. 잠시만 기다려주세요...
echo.

python --version > nul 2>&1
if errorlevel 1 (
    echo Python 3.10 이상을 먼저 설치하세요.
    pause
    exit /b 1
)

if not exist .venv (
    echo [부트스트랩] 가상환경 생성 중...
    python -m venv .venv
)

set PIP_OPTS=
if not "%NEXUS_PYPI%"=="" set PIP_OPTS=--index-url %NEXUS_PYPI% --trusted-host %NEXUS_HOST%
if not "%NEXUS_PYPI%"=="" set PIP_INDEX_URL=%NEXUS_PYPI%

echo [부트스트랩] 기본 패키지(rich, pyyaml) 설치 중...
.venv\Scripts\python.exe -m pip install rich pyyaml %PIP_OPTS% --quiet --disable-pip-version-check

.venv\Scripts\python.exe main.py --setup
echo.
echo 다음부터는 aiu-agent-run.bat 으로 바로 실행할 수 있습니다.
pause
