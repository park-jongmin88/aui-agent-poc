# 설치 가이드

aiu-agent 설치는 **wheel 받기 → install → start** 3단계입니다.

---

## 사전 준비

### 1. Python
- **Python 3.10 이상** 필요 (`Path | None` union 문법 사용)
- 확인: `python --version` (Windows) / `python3 --version` (Linux/Mac)
- 미설치 시 [python.org](https://www.python.org/downloads/) 또는 사내 배포 채널에서 설치
- Windows 설치 시 **"Add Python to PATH"** 체크 필수
- `where python` 으로 경로가 안 나오면 PATH 미등록 상태입니다
  (이 경우 install.bat이 자동으로 `py` 런처를 사용합니다)

### 2. pip 인덱스 (사내 넥서스)
- 사내망에서는 pip이 **사내 넥서스**를 바라보도록 설정되어 있어야 합니다.
- 확인:
  ```bash
  pip config list
  ```
  `global.index-url` 에 넥서스 주소가 보이면 정상입니다.
- 설정이 없다면 (주소는 사내 가이드 참고):
  ```bash
  pip config set global.index-url https://<사내-넥서스-주소>/simple
  pip config set global.trusted-host <사내-넥서스-호스트>
  ```

### 3. 네트워크
- wheel 다운로드 시 넥서스에 접근 가능한 환경이어야 합니다.
- **wheel 동봉 배포본을 받은 경우 설치에는 네트워크가 불필요**합니다.
  (단, 실행 시 LLM·MLflow 서버 연결은 필요합니다)

---

## 1단계: wheel 받기

```bash
# Windows
setting\download_wheels.bat

# Linux/Mac
./setting/download_wheels.sh
```

→ `wheels/` 폴더에 모든 의존성 wheel이 받아집니다.
→ **관리자가 wheels 폴더를 동봉해서 배포하면 이 단계는 불필요합니다.**

---

## 2단계: install

```bash
# Windows
install.bat

# Linux/Mac
./install.sh
```

→ `wheels/` 를 확인하고 로컬 wheel로 설치합니다 (네트워크 불필요).
→ `wheels/` 가 없으면 안내 후 중단됩니다 (1단계부터 실행).
→ 완료되면 start 명령을 안내합니다.

---

## 3단계: 실행

```bash
# Windows
start.bat

# Linux/Mac
./start.sh
```

→ 처음 실행 시 LLM 정보를 대화로 입력받아 `config.json` 을 생성합니다.

---

## 관리자 배포 (권장)

```
관리자
  1. download_wheels 실행 → wheels/ 생성
  2. 프로젝트 + wheels/ 폴더째 ZIP 배포

사용자
  1. ZIP 압축 해제
  2. install 실행 → wheels에서 설치
  3. start 실행
```

- wheels 폴더 용량이 크면 제외하고 배포 가능
  (이 경우 사용자가 1단계부터 직접 실행)
- wheel은 **버전 고정** 방식입니다. 담아준 버전 그대로 설치되며,
  넥서스에서 버전이 바뀌어도 사용자 환경은 변하지 않습니다.
- 업데이트하려면 관리자가 새 wheel을 받아 다시 배포합니다.

---

## 자주 나는 설치 문제

| 증상 | 원인 / 해결 |
|---|---|
| `***는 내부 또는 외부 명령...` | .bat 인코딩 문제 또는 python PATH 미등록. install.bat이 `py` 자동 사용 |
| 첫 install에서 deepagents 실패 | requirements 순서상 deepagents가 마지막에 설치됨 (정상). 다시 install하면 성공 |
| `wheels 폴더가 없거나 부족` | `download_wheels` 를 먼저 실행하세요 |
| 설치가 멈춘 것처럼 보임 | deepagents는 의존성이 많아 시간이 걸립니다 (정상) |

더 자세한 내용은 [troubleshooting.md](troubleshooting.md) 참고.
