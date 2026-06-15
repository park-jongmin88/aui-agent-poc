#!/usr/bin/env bash
# ============================================================
#  aiu-agent wheel 다운로드 (사내 넥서스/PyPI에서 미리 받기)
#  인터넷/넥서스 되는 환경에서 한 번 실행 → wheels/ 폴더 생성
#  이후 install.sh가 wheels/ 를 자동 인식해 빠르게 설치
# ============================================================
set -e
cd "$(dirname "$0")/.."

WHEEL_DIR=wheels
mkdir -p "$WHEEL_DIR"

echo ""
echo "  [wheel 다운로드] 시작"
echo "  대상: requirements.txt + requirements-ml.txt + requirements-serve.txt"
echo ""

python3 -m pip download -r setting/requirements.txt      -d "$WHEEL_DIR"
python3 -m pip download -r setting/requirements-ml.txt    -d "$WHEEL_DIR"
python3 -m pip download -r setting/requirements-serve.txt -d "$WHEEL_DIR"

echo ""
echo "  [wheel 다운로드] 완료 - wheels/ 폴더 확인"
echo "  이제 install.sh를 실행하면 wheels/ 에서 빠르게 설치됩니다."
echo ""
