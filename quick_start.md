# Quick Start — AI-Studio GenAI Agent

설치부터 등록·실행·평가까지 순서대로.

<br>

---

<br>

## 0. 준비물

<br>

- Python 3.11 권장

- MLflow 서버 주소 / 아이디 / 비번

- MLflow AI Gateway 에 LLM 엔드포인트가 등록돼 있을 것

<br>

---

<br>

## 1. 설치

<br>

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

<br>

---

<br>

## 2. 설정

<br>

`config.py` 상단 `[입력란]` 의 MLflow 정보만 채운다.

<br>

```python
MLFLOW_TRACKING_URI = "http://mlflow.도메인.com"
MLFLOW_USERNAME     = "아이디"
MLFLOW_PASSWORD     = "비번"
MLFLOW_EXPERIMENT   = "aiu-agent"
MLFLOW_MODEL_NAME   = "aiu-agent-model"
```

<br>

> LLM 주소·모델은 적지 않는다. 등록할 때 gateway 목록에서 고른다.

<br>

---

<br>

## 3. 에이전트 등록

<br>

```bash
python agent.py
```

<br>

실행하면 gateway 엔드포인트 목록이 뜨고, 사용할 LLM 을 번호로 고른다.

<br>

그다음 자동으로 MLflow 에 모델이 등록된다.

<br>

---

<br>

## 4. 대화 테스트

<br>

`client.py` 상단의 `API_URL` 만 채운 뒤 실행한다.

<br>

```bash
python client.py
```

<br>

프롬프트·버전을 고르고 질문하면 답변이 온다. (LLM 키는 넣지 않는다 — gateway 가 처리)

<br>

---

<br>

## 5. Judge 등록

<br>

```bash
python judge_register.py
```

<br>

3가지를 순서대로 고른다.

<br>

- 평가지 (정확성 / 유용성 / 안전성 / 간결성 / 종합품질)

- 평가용 LLM (gateway 목록에서 선택)

- 자동 트래킹 켜기 / 끄기 (켜면 채점 비율 0.1~1.0 선택)

<br>

---

<br>

## 6. 평가 실행

<br>

```bash
python evaluate.py
```

<br>

등록된 judge 를 골라 최근 trace 를 채점한다. 결과는 MLflow Traces 의 Feedback 에 붙는다.

<br>

> 자동 트래킹을 켜 뒀으면 새 대화는 알아서 채점되므로 이 단계는 수동 평가용이다.

<br>

---

<br>

## 참고 — 조회 도구

<br>

gateway / 프롬프트 / judge 에 뭐가 등록돼 있는지 확인하려면:

<br>

```bash
python mlflow_inspect.py
```

<br>

---

<br>

## 전체 순서 요약

<br>

```bash
pip install -r requirements.txt   # 1. 설치
# config.py 채우기               # 2. 설정
python agent.py                   # 3. 등록
python client.py                  # 4. 대화
python judge_register.py          # 5. judge 등록
python evaluate.py                # 6. 평가
```
