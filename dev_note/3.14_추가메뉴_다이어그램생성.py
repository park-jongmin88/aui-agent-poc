"""3.14 신규 기능(Playground/Review) vs 우리 코드 관계 - 연필 스케치."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

FONT_PATH = "fonts/NanumPenScript-Regular.ttf"
fm.fontManager.addfont(FONT_PATH)
HAND = fm.FontProperties(fname=FONT_PATH).get_name()
plt.rcParams["font.family"] = HAND
plt.rcParams["axes.unicode_minus"] = False

PAPER = "#F7F2E7"
PENCIL = "#5A5A5A"
OURS = "#EAF2F8"     # 우리 코드 (파랑)
UI = "#FDF0E6"       # UI 기능 (주황)
SHARE = "#E9F7EF"    # 공유 데이터 (초록)
FP = fm.FontProperties(fname=FONT_PATH)


def box(ax, x, y, w, h, text, fill, fs=14):
    p = FancyBboxPatch((x, y), w, h,
                       boxstyle="round,pad=0.02,rounding_size=0.12",
                       linewidth=2.2, edgecolor=PENCIL, facecolor=fill)
    ax.add_patch(p)
    ax.text(x + w/2, y + h/2, text, ha="center", va="center",
            fontsize=fs, color=PENCIL, fontproperties=FP)


def arrow(ax, x1, y1, x2, y2, text="", rad=0.0, fs=11):
    a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                        mutation_scale=16, linewidth=1.8, color=PENCIL,
                        connectionstyle=f"arc3,rad={rad}")
    ax.add_patch(a)
    if text:
        ax.text((x1+x2)/2, (y1+y2)/2 + 0.1, text, ha="center", va="bottom",
                fontsize=fs, color=PENCIL, fontproperties=FP)


with plt.xkcd(scale=1.0, length=100, randomness=2):
    fig, ax = plt.subplots(figsize=(14, 9))
    fig.patch.set_facecolor(PAPER)
    ax.set_facecolor(PAPER)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 9)
    ax.axis("off")

    # 제목
    ax.text(7, 8.5, "MLflow 3.14 신규 기능 vs 우리 코드", ha="center",
            fontsize=24, color=PENCIL, fontproperties=FP)
    ax.text(7, 8.0, "( 둘은 별개로 동작 · 같은 데이터를 공유 )", ha="center",
            fontsize=13, color=PENCIL, fontproperties=FP)

    # ── 왼쪽: 우리 코드 (프로그램) ──
    ax.text(3, 7.2, "우리 코드 (터미널 실행)", ha="center",
            fontsize=15, color=PENCIL, fontproperties=FP)
    box(ax, 1.3, 5.7, 3.4, 1.0, "client.py\n대화·프롬프트 테스트", OURS)
    box(ax, 1.3, 4.2, 3.4, 1.0, "evaluate.py\njudge = LLM이 채점", OURS)

    # ── 오른쪽: UI 기능 (3.14) ──
    ax.text(11, 7.2, "MLflow UI 기능 (클릭)", ha="center",
            fontsize=15, color=PENCIL, fontproperties=FP)
    box(ax, 9.3, 5.7, 3.4, 1.0, "Playground\n프롬프트 실험 (UI)", UI)
    box(ax, 9.3, 4.2, 3.4, 1.0, "Review\n사람이 직접 평가 (UI)", UI)

    # ── 가운데: 공유 데이터 ──
    box(ax, 5.6, 5.7, 2.8, 1.0, "Gateway\n엔드포인트", SHARE, fs=13)
    box(ax, 5.6, 4.2, 2.8, 1.0, "Trace\n(대화 기록)", SHARE, fs=13)

    # 연결: Playground <-> Gateway (client도)
    arrow(ax, 4.7, 6.2, 5.6, 6.2, "", rad=0.0)
    arrow(ax, 9.3, 6.2, 8.4, 6.2, "", rad=0.0)
    ax.text(7.0, 6.55, "같은 gateway 사용", ha="center", fontsize=11,
            color=PENCIL, fontproperties=FP)

    # 연결: evaluate/Review <-> Trace
    arrow(ax, 4.7, 4.7, 5.6, 4.7, "", rad=0.0)
    arrow(ax, 9.3, 4.7, 8.4, 4.7, "", rad=0.0)
    ax.text(7.0, 5.05, "같은 trace 평가", ha="center", fontsize=11,
            color=PENCIL, fontproperties=FP)

    # ── 하단: 비교 요약 ──
    box(ax, 1.3, 2.1, 5.5, 1.4,
        "Playground vs client.py\n· Playground = 프롬프트만 빠르게 (UI)\n· client.py = 전체 파이프라인(RAG 포함)",
        "#F5EEF8", fs=12)
    box(ax, 7.2, 2.1, 5.5, 1.4,
        "Review vs judge\n· Review = 사람이 평가 (인증 불필요!)\n· judge = LLM이 평가 (자동, 지금 인증 막힘)",
        "#F5EEF8", fs=12)

    # ── 맨 아래: 버전 안내 ──
    box(ax, 3.5, 0.4, 7.0, 1.1,
        "지금은 3.13 → 이 두 UI 기능 없음\n쓰려면 3.14 업그레이드 필요 (Review는 인증 막힌 지금 대안)",
        "#FEF9E7", fs=12)

    fig.savefig("mlflow314_vs_ours.png", dpi=200, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    fig.savefig("mlflow314_vs_ours.svg", bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    print("생성 완료")
