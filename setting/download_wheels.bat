@echo off
REM ============================================================
REM  aiu-agent wheel 다운로드 (사내 넥서스/PyPI에서 미리 받기)
REM  인터넷/넥서스 되는 환경에서 한 번 실행 → wheels/ 폴더 생성
REM  이후 install.bat이 wheels/ 를 자동 인식해 빠르게 설치
REM ============================================================
setlocal
cd /d "%~dp0\.."

set WHEEL_DIR=wheels
if not exist "%WHEEL_DIR%" mkdir "%WHEEL_DIR%"

REM Python 실행 명령 자동 판별 (python이 PATH에 없으면 py 런처)
set PYCMD=python
python --version >nul 2>&1
if not errorlevel 1 goto :pyfound
set PYCMD=py
py --version >nul 2>&1
if not errorlevel 1 goto :pyfound
echo Python 이 설치되어 있지 않거나 PATH에 없습니다.
echo python.org 에서 설치 후 "Add Python to PATH" 체크하세요.
pause
exit /b 1
:pyfound

echo.
echo  [wheel 다운로드] 시작
echo  대상: requirements.txt (전체 의존성)
echo.

%PYCMD% -m pip download -r setting\requirements.txt -d "%WHEEL_DIR%"

echo.
echo  [wheel 다운로드] 완료 - wheels\ 폴더 확인
echo  이제 install.bat을 실행하면 wheels\ 에서 빠르게 설치됩니다.
echo.
pause
endlocal