import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# 한글 폰트 설정
_nanum = next((f.fname for f in fm.fontManager.ttflist if 'NanumGothic' in f.name and 'Coding' not in f.name), None)
if _nanum:
    plt.rcParams['font.family'] = 'NanumGothic'
plt.rcParams['axes.unicode_minus'] = False
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patheffects as pe

fig = plt.figure(figsize=(22, 28), facecolor='#0d1117')
fig.patch.set_facecolor('#0d1117')

ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 22)
ax.set_ylim(0, 28)
ax.axis('off')
ax.set_facecolor('#0d1117')

# ── 색상 팔레트 ─────────────────────────────────────────────
C = {
    'bg':       '#0d1117',
    'panel':    '#161b22',
    'border':   '#30363d',
    'cyan':     '#58a6ff',
    'green':    '#3fb950',
    'yellow':   '#d29922',
    'orange':   '#f0883e',
    'purple':   '#bc8cff',
    'red':      '#f85149',
    'grey':     '#8b949e',
    'white':    '#e6edf3',
    'teal':     '#39d353',
}

def panel(ax, x, y, w, h, color=C['panel'], border=C['border'], radius=0.3, alpha=1.0):
    box = FancyBboxPatch((x, y), w, h,
        boxstyle=f"round,pad=0,rounding_size={radius}",
        facecolor=color, edgecolor=border, linewidth=1.2, alpha=alpha, zorder=2)
    ax.add_patch(box)

def txt(ax, x, y, s, size=10, color=C['white'], weight='normal', ha='center', va='center', zorder=5):
    ax.text(x, y, s, fontsize=size, color=color, fontweight=weight,
            ha=ha, va=va, zorder=zorder,
            )

def arrow(ax, x1, y1, x2, y2, color=C['grey'], lw=1.5, style='->', zorder=3):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
        arrowprops=dict(arrowstyle=style, color=color, lw=lw),
        zorder=zorder)

# ══════════════════════════════════════════════════════════════
# 제목
# ══════════════════════════════════════════════════════════════
panel(ax, 0.3, 26.5, 21.4, 1.2, color='#1c2128', border=C['cyan'])
txt(ax, 11, 27.2, '🐳  aiu-agent  —  AI STUDIO 자동화 어시스턴트', size=18, color=C['cyan'], weight='bold')
txt(ax, 11, 26.75, 'LangChain DeepAgents 기반  |  MLflow 연동  |  단계별 게이트 시스템', size=11, color=C['grey'])

# ══════════════════════════════════════════════════════════════
# 섹션 1: 설치/실행 흐름
# ══════════════════════════════════════════════════════════════
panel(ax, 0.3, 23.8, 10.2, 2.4, color='#1c2128', border=C['border'])
txt(ax, 1.0, 25.9, '⚙  설치 / 실행', size=12, color=C['yellow'], weight='bold', ha='left')

steps = [
    ('install.bat / .sh', '#21262d', C['orange']),
    ('venv 생성', '#21262d', C['grey']),
    ('패키지 설치', '#21262d', C['grey']),
    ('start.bat / .sh', '#21262d', C['green']),
]
sx = 0.7
for i, (label, bg, fc) in enumerate(steps):
    panel(ax, sx, 24.1, 2.1, 0.65, color=bg, border=fc, radius=0.2)
    txt(ax, sx+1.05, 24.43, label, size=8.5, color=fc, weight='bold')
    if i < len(steps)-1:
        arrow(ax, sx+2.1, 24.43, sx+2.3, 24.43, color=C['grey'], lw=1.2)
    sx += 2.5

txt(ax, 5.4, 23.95, '처음 한 번만  →  이후는 start.bat/sh 로 바로 실행', size=8, color=C['grey'])

# ══════════════════════════════════════════════════════════════
# 섹션 2: LLM + MLflow 설정
# ══════════════════════════════════════════════════════════════
panel(ax, 10.8, 23.8, 11.1, 2.4, color='#1c2128', border=C['border'])
txt(ax, 11.4, 25.9, '🔧  설정  (config.json)', size=12, color=C['yellow'], weight='bold', ha='left')

panel(ax, 11.0, 24.05, 4.8, 1.55, color='#21262d', border=C['purple'], radius=0.2)
txt(ax, 13.4, 25.35, 'LLM 설정', size=9, color=C['purple'], weight='bold')
txt(ax, 13.4, 24.95, 'type: openai | anthropic', size=8, color=C['grey'])
txt(ax, 13.4, 24.65, 'base_url / api_key / model', size=8, color=C['grey'])
txt(ax, 13.4, 24.35, 'active: 현재 사용 LLM', size=8, color=C['grey'])

panel(ax, 16.1, 24.05, 5.5, 1.55, color='#21262d', border=C['cyan'], radius=0.2)
txt(ax, 18.85, 25.35, 'MLflow 설정', size=9, color=C['cyan'], weight='bold')
txt(ax, 18.85, 24.95, 'tracking_uri: http://mlflow:5000', size=8, color=C['grey'])
txt(ax, 18.85, 24.65, 'username / password', size=8, color=C['grey'])
txt(ax, 18.85, 24.35, '모든 모델 공통 사용', size=8, color=C['grey'])

# ══════════════════════════════════════════════════════════════
# 섹션 3: 작업 공간 구조
# ══════════════════════════════════════════════════════════════
panel(ax, 0.3, 20.0, 10.2, 3.5, color='#1c2128', border=C['border'])
txt(ax, 1.0, 23.2, '📁  workspace/ 구조', size=12, color=C['yellow'], weight='bold', ha='left')

ws_items = [
    ('workspace/', C['white'], 9, False),
    ('  .current', C['cyan'], 8.5, False),
    ('  models/', C['white'], 8.5, False),
    ('    <모델명>/', C['orange'], 8.5, False),
    ('      source/   ← 원본 자료 (데이터/코드/모델)', C['grey'], 8, False),
    ('      run.py    ← init이 자동 생성', C['green'], 8, False),
    ('      .aiu_state.json  ← 단계 상태', C['purple'], 8, False),
    ('  templates/   ← run.py 베이스 (수정금지)', C['grey'], 8, False),
    ('  results/     ← 로컬 학습 결과물', C['grey'], 8, False),
]
yy = 22.85
for item, col, sz, bold in ws_items:
    txt(ax, 0.65, yy, item, size=sz, color=col, ha='left')
    yy -= 0.32

# 샘플 폴더
panel(ax, 0.3, 16.5, 10.2, 3.2, color='#1c2128', border=C['border'])
txt(ax, 1.0, 19.4, '📦  샘플 모델 폴더', size=12, color=C['yellow'], weight='bold', ha='left')

samples = [
    ('sklearn_sample/',     'DATA_ONLY',   'CSV 분류 데이터',          C['cyan']),
    ('sklearn_pretrained/', 'LOAD_MODEL',  '학습된 RF .pkl',           C['green']),
    ('custom_code_sample/', 'RUN_CODE',    'SVM 학습 코드 .py',        C['orange']),
    ('multifile_sample/',   '혼합',        'CSV + 전처리 코드',         C['purple']),
    ('template_only/',      'TEMPLATE',    '빈 폴더 (처음부터 작성)',   C['grey']),
    ('pytorch_sample/',     'TEMPLATE',    'PyTorch 시작용',           C['grey']),
    ('tensorflow_sample/',  'TEMPLATE',    'TF/Keras 시작용',          C['grey']),
]
yy = 19.0
for fname, mode, desc, col in samples:
    txt(ax, 0.8, yy, f'• {fname}', size=8.5, color=col, ha='left')
    txt(ax, 5.5, yy, f'[{mode}]', size=8, color=col, ha='left')
    txt(ax, 7.5, yy, desc, size=8, color=C['grey'], ha='left')
    yy -= 0.38

# ══════════════════════════════════════════════════════════════
# 섹션 4: 단계별 게이트 시스템 (메인)
# ══════════════════════════════════════════════════════════════
panel(ax, 10.8, 16.5, 11.1, 7.0, color='#1c2128', border=C['border'])
txt(ax, 11.4, 23.2, '🔁  단계별 게이트 시스템', size=12, color=C['yellow'], weight='bold', ha='left')

stages = [
    ('① init',       'source/ 분석 → run.py 자동 생성\n모드 판별: LOAD_MODEL / RUN_CODE\n        DATA_ONLY / TEMPLATE\n실험명/모델명 확인 후 섹션2 자동 채움',  C['cyan'],   'initialized',  True),
    ('② validate',   '9섹션 구조 검증\nTODO/NotImplementedError 확인\nMLflow 설정 확인',                                                               C['green'],  'validated',    True),
    ('③ local_run',  'MLflow 없이 로컬 학습 (선택)\n결과 → workspace/results/\n로컬 서빙 연계 가능',                                                     C['grey'],   'local_tested', False),
    ('④ train',      'run.py 실행 → MLflow 등록\nML 패키지 자동 설치 확인\n실시간 출력 스트리밍',                                                       C['orange'], 'trained',      True),
    ('⑤ predict',    'MLflow 모델 로드\n추론 테스트 (input_example)',                                                                                    C['purple'], 'predicted',    True),
    ('⑥ local_serve','workspace/results/ 모델\nFastAPI 서빙 (선택)\nPOST /predict 엔드포인트',                                                         C['teal'],   'serving',      False),
    ('⑦ deploy',     'POC: 절차 안내만\n향후: 포털 API 연동',                                                                                           C['red'],    'deployed',     True),
]

sy = 22.7
for i, (name, desc, col, status, required) in enumerate(stages):
    bdr = col if required else C['border']
    panel(ax, 11.0, sy-0.85, 10.7, 0.95, color='#21262d', border=bdr, radius=0.2)
    txt(ax, 11.3, sy-0.35, name, size=9.5, color=col, weight='bold', ha='left')
    opt = '' if required else '  [선택]'
    txt(ax, 21.4, sy-0.35, opt, size=8, color=C['grey'], ha='right')
    lines = desc.split('\n')
    for j, line in enumerate(lines):
        txt(ax, 14.5, sy-0.28-j*0.22, line.strip(), size=7.5, color=C['grey'], ha='left')
    txt(ax, 20.5, sy-0.65, f'→ status={status}', size=7.5, color=col, ha='right')

    if i < len(stages)-1:
        next_required = stages[i+1][5] if len(stages[i+1]) > 5 else True
        arr_col = col if required else C['border']
        ax.annotate('', xy=(15.5, sy-0.88), xytext=(15.5, sy-0.82),
            arrowprops=dict(arrowstyle='->', color=arr_col, lw=1.2), zorder=4)
    sy -= 1.05

# ══════════════════════════════════════════════════════════════
# 섹션 5: CLI 화면 예시
# ══════════════════════════════════════════════════════════════
panel(ax, 0.3, 12.8, 10.2, 3.4, color='#1c2128', border=C['border'])
txt(ax, 1.0, 15.9, '💻  CLI 화면 예시', size=12, color=C['yellow'], weight='bold', ha='left')

panel(ax, 0.5, 13.0, 9.8, 2.7, color='#010409', border=C['border'], radius=0.15)
cli_lines = [
    ('> 검증해줘', C['white'], 8.5),
    ('', C['grey'], 7),
    ('────────────────────────────────────', C['border'], 7),
    ('🐳 run.py 검증 완료.', C['green'], 8.5),
    ('   9섹션 ✓  TODO 없음 ✓  MLflow ✓', C['grey'], 8),
    ('   → 학습을 시작할 수 있습니다.', C['cyan'], 8),
    ('────────────────────────────────────', C['border'], 7),
    ('━━ 📁 sklearn_sample │ ✅init ──▶ ✅validate ──▶ [train] ──▶ ○predict ━━', C['cyan'], 7.5),
    ('❯', C['white'], 9),
]
yy = 15.5
for line, col, sz in cli_lines:
    txt(ax, 0.75, yy, line, size=sz, color=col, ha='left')
    yy -= 0.27

# ══════════════════════════════════════════════════════════════
# 섹션 6: run.py 9섹션 구조
# ══════════════════════════════════════════════════════════════
panel(ax, 10.8, 12.8, 11.1, 3.4, color='#1c2128', border=C['border'])
txt(ax, 11.4, 15.9, '📄  run.py  9-섹션 표준', size=12, color=C['yellow'], weight='bold', ha='left')

sections = [
    ('1. 임포트',          '자동',   C['green'],  'sklearn/torch/tf 자동 선택'),
    ('2. MLflow 연동',     '자동',   C['green'],  'config.json 값 자동 채움'),
    ('3. 데이터 준비',     '자동',   C['green'],  'CSV/npy 로드 코드 자동 생성'),
    ('4. 모델 준비',       '반자동', C['orange'], 'pkl/h5 자동, 구조정의는 TODO'),
    ('5. 트레이닝',        '반자동', C['orange'], '기본 fit() 자동, 튜닝은 TODO'),
    ('6. 인풋 샘플',       '자동',   C['green'],  'X[:5] 자동 생성'),
    ('7. MLflow 로깅',     '자동',   C['green'],  '프레임워크별 log_model 자동'),
    ('8. config.json',    '자동',   C['green'],  '모델명 저장'),
    ('9. 런 스타트',       '자동',   C['green'],  'mlflow.start_run() 자동'),
]
col1x, col2x, col3x, col4x = 11.2, 14.2, 15.4, 16.5
yy = 15.55
for sec, auto, col, desc in sections:
    txt(ax, col1x, yy, sec, size=8, color=C['white'], ha='left')
    txt(ax, col2x, yy, f'[{auto}]', size=7.5, color=col, ha='left')
    txt(ax, col4x, yy, desc, size=7.5, color=C['grey'], ha='left')
    yy -= 0.33

# ══════════════════════════════════════════════════════════════
# 섹션 7: 명령어
# ══════════════════════════════════════════════════════════════
panel(ax, 0.3, 9.5, 10.2, 3.0, color='#1c2128', border=C['border'])
txt(ax, 1.0, 12.2, '⌨  명령어', size=12, color=C['yellow'], weight='bold', ha='left')

cmds = [
    ('/? /help',  '도움말 (작업 안내 포함)',      C['cyan']),
    ('/list',     '작업 폴더 목록 (번호 선택)',   C['cyan']),
    ('/llm',      'LLM 목록 + 전환',             C['purple']),
    ('/reload',   'config.json 재로드',          C['orange']),
    ('/config',   '현재 설정 확인',              C['grey']),
    ('/log',      '마지막 로그 확인',            C['grey']),
    ('/clear',    '대화 초기화',                 C['grey']),
    ('/exit',     '종료',                        C['red']),
]
yy = 11.9
for cmd, desc, col in cmds:
    txt(ax, 0.8, yy, cmd, size=8.5, color=col, weight='bold', ha='left')
    txt(ax, 3.2, yy, desc, size=8.5, color=C['grey'], ha='left')
    yy -= 0.33

# ══════════════════════════════════════════════════════════════
# 섹션 8: 기술 스택
# ══════════════════════════════════════════════════════════════
panel(ax, 10.8, 9.5, 11.1, 3.0, color='#1c2128', border=C['border'])
txt(ax, 11.4, 12.2, '🔩  기술 스택', size=12, color=C['yellow'], weight='bold', ha='left')

stacks = [
    ('에이전트',   'LangChain DeepAgents',              C['cyan']),
    ('LLM',       'OpenAI 호환 / Anthropic',            C['purple']),
    ('ML 등록',   'MLflow (모델 레지스트리)',            C['orange']),
    ('CLI',       'prompt_toolkit + rich',              C['green']),
    ('설정',      'config.json (표준 json)',             C['grey']),
    ('프레임워크', 'sklearn / PyTorch / TensorFlow',    C['teal']),
    ('서빙',      'FastAPI (local_serve)',               C['cyan']),
    ('배포',      'ZIP → install.bat/sh',               C['grey']),
]
yy = 11.9
for cat, val, col in stacks:
    txt(ax, 11.2, yy, f'{cat}:', size=8.5, color=C['grey'], ha='left')
    txt(ax, 14.0, yy, val, size=8.5, color=col, ha='left')
    yy -= 0.33

# ══════════════════════════════════════════════════════════════
# 섹션 9: 핵심 파일 구조
# ══════════════════════════════════════════════════════════════
panel(ax, 0.3, 5.5, 21.4, 3.7, color='#1c2128', border=C['border'])
txt(ax, 1.0, 8.9, '🗂  핵심 파일 구조', size=12, color=C['yellow'], weight='bold', ha='left')

files = [
    (0.7,  'main.py',                    C['cyan'],   '진입점 (CLI 루프, --setup/--check 모드)'),
    (0.7,  'agent.md',                   C['green'],  '에이전트 정의 (게이트, 작업흐름, 구조)'),
    (0.7,  'config.json',                C['orange'], 'LLM + MLflow 설정 (자동생성, .gitignore)'),
    (0.7,  'config.sample.json',         C['grey'],   '설정 예시 (groq/openai/anthropic/ollama)'),
    (0.7,  'install.bat / install.sh',   C['grey'],   '최초 설치 (입력없음) → start.bat/sh 생성'),
    (0.7,  'skills/common/__init__.py',  C['purple'], '공통 유틸 (게이트/상태관리/MLflow 설정)'),
    (0.7,  'skills/init/scripts/generate_run.py', C['cyan'], 'run.py 자동 생성 (모드별 섹션 생성)'),
    (0.7,  'skills/validate/scripts/validate_run.py', C['green'], 'run.py 구조+내용 검증 (9섹션/TODO/MLflow)'),
    (0.7,  'setting/requirements.txt',   C['grey'],   '에이전트 구동 (deepagents/langchain)'),
    (0.7,  'setting/requirements-ml.txt',C['orange'], 'ML 작업 (mlflow/sklearn/pandas/numpy)'),
]
yy = 8.6
col_offset = 11.0
for i, (x, fname, col, desc) in enumerate(files):
    cx = x if i < 5 else x + col_offset - 0.3
    cy = yy if i < 5 else (8.6 - (i-5) * 0.62)
    if i == 5:
        yy_right = 8.6
    txt(ax, cx, cy, f'• {fname}', size=8.2, color=col, ha='left')
    txt(ax, cx + 4.2, cy, desc, size=8, color=C['grey'], ha='left')
    if i < 5:
        yy -= 0.62

# ══════════════════════════════════════════════════════════════
# 섹션 10: 흐름 요약
# ══════════════════════════════════════════════════════════════
panel(ax, 0.3, 2.8, 21.4, 2.4, color='#161b22', border=C['cyan'], radius=0.3)
txt(ax, 11, 4.9, '🐳  전체 흐름 요약', size=12, color=C['cyan'], weight='bold')

flow = [
    ('install', C['orange']), ('→', C['grey']), ('start', C['green']), ('→', C['grey']),
    ('LLM 설정', C['purple']), ('→', C['grey']), ('폴더 선택', C['cyan']), ('→', C['grey']),
    ('init', C['cyan']), ('→', C['grey']), ('validate', C['green']), ('→', C['grey']),
    ('[local_run]', C['grey']), ('→', C['grey']), ('train', C['orange']), ('→', C['grey']),
    ('predict', C['purple']), ('→', C['grey']), ('[local_serve]', C['teal']), ('→', C['grey']),
    ('deploy', C['red']),
]
fx = 0.8
for label, col in flow:
    txt(ax, fx, 4.3, label, size=9, color=col, weight='bold' if label not in ('→',) else 'normal', ha='left')
    fx += len(label) * 0.38 + 0.15

txt(ax, 11, 3.85, '[ ] 는 선택 단계  |  각 단계는 이전 단계 통과 후 진행 가능  |  게이트 실패 시 안내 후 차단', size=9, color=C['grey'])
txt(ax, 11, 3.4, '재접속 시 마지막 작업 상태 자동 안내  |  하단 상태바에 현재 진행 단계 항상 표시', size=9, color=C['grey'])
txt(ax, 11, 2.95, 'MLflow 주소는 config.json 공통 설정  |  실험명/모델명은 폴더별 .aiu_state.json 관리', size=9, color=C['grey'])

# ── 푸터 ───────────────────────────────────────────────────
txt(ax, 11, 2.4, 'aiu-agent  v0.2.0 (POC)  |  park-jongmin88/aui-agent-poc', size=9, color=C['grey'])

plt.savefig('/mnt/user-data/outputs/aiu-agent-overview.png',
            dpi=150, bbox_inches='tight',
            facecolor='#0d1117', edgecolor='none')
print("완료")
