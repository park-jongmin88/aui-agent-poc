@echo off

REM ====================================================
REM  [운영자 설정] 사내 넥서스 PyPI 주소
REM  비워두면 PC의 기본 pip 설정을 따릅니다.
REM  예) set NEXUS_PYPI=http://nexus.company.com/repository/pypi-proxy/simple
REM      set NEXUS_HOST=nexus.company.com
REM ====================================================
set NEXUS_PYPI=
set NEXUS_HOST=

echo ====================================================
echo    AIU DeepAgent - Quick Start (설치)
echo ====================================================
echo.

REM [1/4] Python 확인
python --version > nul 2>&1
if errorlevel 1 (
    echo   [1/4] Python 확인 ... 실패
    echo         Python 3.10 이상을 먼저 설치하세요.
    pause
    exit /b 1
)
echo   [1/4] Python 확인 ... OK

REM [2/4] 가상환경 생성
if not exist .venv (
    echo   [2/4] 가상환경 생성 중...
    python -m venv .venv
)
echo   [2/4] 가상환경 ... OK

REM [3/4] 의존성 설치
set PIP_OPTS=
if not "%NEXUS_PYPI%"=="" set PIP_OPTS=--index-url %NEXUS_PYPI% --trusted-host %NEXUS_HOST%
echo   [3/4] 의존성 설치 중... (수 분 소요)
call .venv\Scripts\activate.bat
pip install -r setting\requirements.txt %PIP_OPTS%
if errorlevel 1 (
    echo   [3/4] 의존성 설치 ... 실패
    pause
    exit /b 1
)
echo   [3/4] 의존성 설치 ... OK

REM [4/4] .env 확인
if not exist .env (
    copy .env.example .env > nul
    echo   [4/4] .env 생성 ... OK  값을 채워주세요!
) else (
    echo   [4/4] .env 확인 ... OK
)

echo.
echo ====================================================
echo   설치 완료!
echo   1. .env 파일을 열어 TODO 항목을 채우세요.
echo   2. 실행:  .venv\Scripts\activate  후  python main.py
echo ====================================================
pause
