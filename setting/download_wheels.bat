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

echo.
echo  [wheel 다운로드] 시작
echo  대상: requirements.txt + requirements-ml.txt + requirements-serve.txt
echo.

python -m pip download -r setting\requirements.txt          -d "%WHEEL_DIR%"
python -m pip download -r setting\requirements-ml.txt        -d "%WHEEL_DIR%"
python -m pip download -r setting\requirements-serve.txt     -d "%WHEEL_DIR%"

echo.
echo  [wheel 다운로드] 완료 - wheels\ 폴더 확인
echo  이제 install.bat을 실행하면 wheels\ 에서 빠르게 설치됩니다.
echo.
pause
endlocal
