# aiu-agent (POC)

🐳 **AI STUDIO 자동화 어시스턴트** — LangChain DeepAgents 기반 ML/DL 프로세스 CLI 자동화.

ML/DL 개발자가 자연어로 요청하면, 코드를 만들고 MLflow에 등록해주는 대화형 CLI 도구입니다.

---

## 빠른 시작

```bash
setting\download_wheels.bat   # 1. wheel 받기 (관리자 배포본은 생략)
install.bat                   # 2. 설치
start.bat                     # 3. 실행
```

Linux/Mac은 `.sh` 스크립트를 사용하세요.

---

## 문서

- 📦 **[설치 가이드](docs/INSTALL.md)** — 사전 준비, wheel 받기, 설치, 관리자 배포 방법
- 📖 **[사용 설명서](docs/MANUAL.md)** — 작업 흐름, 용어, 모드, 게이트, 상태, 명령어
- 🔧 **[문제 해결](docs/troubleshooting.md)** — 자주 나는 오류와 해결법

---

## 핵심 흐름

```
0. 모델 선택  →  1. 준비  →  2. 검증  →  3. 로컬테스트(선택)
                                              ↓
        7. 배포  ←  6. 로컬서빙(선택)  ←  5. 추론  ←  4. 학습
```

- 각 단계는 앞 단계를 통과해야 진행됩니다 (게이트)
- **모든 모델은 pyfunc + ModelWrapper로 MLflow에 등록**됩니다

자세한 흐름과 용어는 [사용 설명서](docs/MANUAL.md)를 참고하세요.

---

## 프로젝트 구조

```
install.bat / start.bat   설치 / 실행 스크립트
main.py                   에이전트 진입점
agent.md                  에이전트 정의 (게이트, pyfunc 표준)
config.json               LLM + MLflow 설정 (.gitignore)

setting/                  requirements.txt, download_wheels
skills/                   init, validate, localrun, train, predict, localserve, deploy
docs/                     문서 모음
workspace/                작업 폴더 (models/, results/, templates/)
```
