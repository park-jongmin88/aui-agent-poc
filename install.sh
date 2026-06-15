#!/usr/bin/env bash

# ====================================================
#  [운영자 설정] 사내 넥서스 PyPI 주소 (비우면 기본 pip)
#  예) NEXUS_PYPI=http://nexus.company.com/repository/pypi-proxy/simple
# ====================================================
NEXUS_PYPI=""

echo "🐳 aiu-agent 준비 중입니다. 잠시만 기다려주세요..."
echo

if ! command -v python3 > /dev/null; then
    echo "Python 3.10 이상을 먼저 설치하세요."
    exit 1
fi

if [ ! -d .venv ]; then
    echo "🐳 가상환경 생성 중..."
    python3 -m venv .venv
fi

PIP_OPTS=""
if [ -n "$NEXUS_PYPI" ]; then
    PIP_OPTS="--index-url $NEXUS_PYPI"
    export PIP_INDEX_URL="$NEXUS_PYPI"
fi



.venv/bin/python main.py --setup
EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
    echo
    echo "  ┌─ 설치 중 문제가 발생했습니다 ─────────────────"
    echo "  │ 위 메시지에서 원인을 확인하세요."
    echo "  │"
    echo "  │ 주요 원인:"
    echo "  │   - LLM 연결 실패: config.json 의 base_url/api_key/type 확인"
    echo "  │   - 의존성 설치 실패: 네트워크 또는 넥서스 설정 확인"
    echo "  │   - 설정 누락: config.json 의 TODO 항목 미입력"
    echo "  │"
    echo "  │ 수정 후 ./start.sh 로 재실행하세요."
    echo "  └──────────────────────────────────────────────"
    exit $EXIT_CODE
fi

echo
echo "다음부터는 ./start.sh 으로 바로 실행할 수 있습니다."
