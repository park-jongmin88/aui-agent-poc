#!/usr/bin/env bash
set -e

# ====================================================
#  [운영자 설정] 사내 넥서스 PyPI 주소 (비우면 기본 pip)
#  예) NEXUS_PYPI=http://nexus.company.com/repository/pypi-proxy/simple
# ====================================================
NEXUS_PYPI=""

echo "aiu-agent 준비 중입니다. 잠시만 기다려주세요..."
echo

if ! command -v python3 > /dev/null; then
    echo "Python 3.10 이상을 먼저 설치하세요."
    exit 1
fi

if [ ! -d .venv ]; then
    echo "[부트스트랩] 가상환경 생성 중..."
    python3 -m venv .venv
fi

PIP_OPTS=""
if [ -n "$NEXUS_PYPI" ]; then
    PIP_OPTS="--index-url $NEXUS_PYPI"
    export PIP_INDEX_URL="$NEXUS_PYPI"
fi

echo "[부트스트랩] 기본 패키지(rich, pyyaml) 설치 중..."
.venv/bin/python -m pip install rich pyyaml "ruamel.yaml" $PIP_OPTS --quiet --disable-pip-version-check

# 실행 스크립트 생성 (다음부터는 이 파일로 바로 실행)
cat > aiu-agent-run.sh << 'RUNEOF'
#!/usr/bin/env bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$DIR/.venv/bin/python" "$DIR/main.py" "$@"
RUNEOF
chmod +x aiu-agent-run.sh

.venv/bin/python main.py --setup

echo
echo "다음부터는 ./start.sh 으로 바로 실행할 수 있습니다."
