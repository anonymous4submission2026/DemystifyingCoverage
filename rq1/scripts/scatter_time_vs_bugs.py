import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from collections import defaultdict

# -----------------------------
# Configuration (fixed order)
# -----------------------------
configs = [
    "allcov",
    "allcov-lexer",
    "allcov-lexer-parser",
    "allcov-lexer-parser-typechecker",
    "allcov-lexer-parser-typechecker-irgen",
    "allcov-lexer-parser-typechecker-irgen-opt",
    "nocov",
]

# -----------------------------
# Hardcoded Data
# -----------------------------
gcc_data = {
    "allcov":                                    (4, 64),
    "allcov-lexer":                              (4, 62),
    "allcov-lexer-parser":                       (6, 60),
    "allcov-lexer-parser-typechecker":           (7, 54),
    "allcov-lexer-parser-typechecker-irgen":     (8, 35),
    "allcov-lexer-parser-typechecker-irgen-opt": (10, 35),
    "nocov":                                     (8, 21),
}

llvm_data = {
    "allcov":                                    (14, 48),
    "allcov-lexer":                              (15, 48),
    "allcov-lexer-parser":                       (14, 44),
    "allcov-lexer-parser-typechecker":           (14, 42),
    "allcov-lexer-parser-typechecker-irgen":     (15, 31),
    "allcov-lexer-parser-typechecker-irgen-opt": (17, 31),
    "nocov":                                     (14, 26),
}

# -----------------------------
# Colorblind-safe palette (Okabe–Ito)
# -----------------------------
color_map = {
    "allcov": "#0072B2",
    "allcov-lexer": "#E69F00",
    "allcov-lexer-parser": "#009E73",
    "allcov-lexer-parser-typechecker": "#D55E00",
    "allcov-lexer-parser-typechecker-irgen": "#CC79A7",
    "allcov-lexer-parser-typechecker-irgen-opt": "#56B4E9",
    "nocov": "#000000",
}

# -----------------------------
# Deterministic offsets
# -----------------------------
OFFSETS = [
    (0.00, 0.00),
    (0.08, 0.00),
    (-0.08, 0.00),
    (0.00, 0.30),
    (0.00, -0.30),
    (0.06, 0.20),
    (-0.06, -0.20),
]

# -----------------------------
# Global font control
# -----------------------------
plt.rcParams.update({
    "font.size": 10,
    "axes.labelsize": 11,
    "axes.titlesize": 12,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
})

# -----------------------------
# Compute shared Y-axis
# -----------------------------
all_y = [v[1] for v in gcc_data.values()] + [v[1] for v in llvm_data.values()]
ymin = min(all_y) - 5
ymax = max(all_y) + 5

# -----------------------------
# Shared plotting logic
# -----------------------------
def draw_subplot(ax, data, title):
    ax.set_axisbelow(True)
    ax.set_facecolor("white")

    # subtle grid
    ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.5)

    xs, ys = [], []

    point_map = defaultdict(list)
    for cfg in configs:
        point_map[data[cfg]].append(cfg)

    for (x, y), cfgs in point_map.items():
        for i, cfg in enumerate(cfgs):
            dx, dy = OFFSETS[i % len(OFFSETS)]

            ax.scatter(
                x + dx,
                y + dy,
                color=color_map[cfg],
                s=110,
                edgecolors="black",
                linewidth=0.8,
                zorder=3
            )

        xs.append(x)
        ys.append(y)

    # cleaner titles
    ax.set_title(title)

    ax.set_xlabel("Deep Bugs Detected")
    ax.set_ylabel("Compilation Time (sec / 1K files)")

    # X ticks
    x_min, x_max = min(xs), max(xs)
    ax.set_xticks(range(int(x_min) - 1, int(x_max) + 2))

    # shared Y scale
    ax.set_ylim(ymin, ymax)

# -----------------------------
# Create subplots
# -----------------------------
fig, axes = plt.subplots(2, 1, figsize=(6.5, 7.5), sharey=True)

draw_subplot(axes[0], llvm_data, "CLANG")
draw_subplot(axes[1], gcc_data, "GCC")

# -----------------------------
# Legend (clean + horizontal)
# -----------------------------
handles = [
    plt.Line2D(
        [0], [0],
        marker='o',
        linestyle='',
        color=color_map[cfg],
        markeredgecolor='black',
        markersize=9
    )
    for cfg in configs
]

fig.legend(
    handles,
    [f"C{i+1}="+cfg for (i, cfg) in enumerate(configs)],
    loc="lower center",
    ncol=4,
    frameon=True,
    bbox_to_anchor=(0.49, -0.02)
)

# -----------------------------
# Layout + Save
# -----------------------------
plt.subplots_adjust(hspace=0.35, bottom=0.125)

plt.savefig("time_vs_deep_bugs.png", dpi=300, bbox_inches="tight")