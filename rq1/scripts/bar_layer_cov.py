import matplotlib
matplotlib.use("Agg")

import numpy as np
import matplotlib.pyplot as plt

# -----------------------------------
# Data
# -----------------------------------
categories = ["lexer", "parser", "typechecker", "ir-gen", "opt", "codegen"]

llvm_allcov = [7.55, 4.18, 7.92, 8.92, 20.79, 7.24]
llvm_nocov  = [7.79, 4.97, 8.99, 8.93, 21.28, 7.59]

gcc_allcov  = [23.90, 6.15, 15.22, 21.94, 39.45, 12.79]
gcc_nocov   = [24.72, 7.37, 17.12, 22.07, 40.03, 12.94]

labels = ["lex", "parse", "type", "ir", "opt", "code"]

# -----------------------------------
# Plot Helper
# -----------------------------------
def create_bar_plot(ax, allcov, nocov, title):
    x = np.arange(len(labels))
    width = 0.35

    bars1 = ax.bar(x - width/2, allcov, width, label="allcov")
    bars2 = ax.bar(x + width/2, nocov,  width, label="nocov")

    ax.set_title(title, fontsize=16)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=14)
    ax.tick_params(axis='y', labelsize=13)

    all_vals = allcov + nocov
    vmin = min(all_vals)
    vmax = max(all_vals)
    margin = max((vmax - vmin) * 0.2, 0.5)
    ax.set_ylim(vmin - margin, vmax + margin)

    ax.grid(axis='y', linestyle='--', linewidth=0.5, alpha=0.3)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    for bar in bars1:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width()/2,
            height,
            f"{height:.2f}",
            ha='center',
            va='bottom',
            fontsize=11
        )

    for bar in bars2:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width()/2,
            height,
            f"{height:.2f}",
            ha='center',
            va='bottom',
            fontsize=11
        )

    ax.legend(frameon=False, fontsize=13)


# -----------------------------------
# Main Figure
# -----------------------------------
fig, axes = plt.subplots(2, 1, figsize=(8, 8))

create_bar_plot(axes[0], llvm_allcov, llvm_nocov, "LLVM Coverage Comparison")
create_bar_plot(axes[1], gcc_allcov,  gcc_nocov,  "GCC Coverage Comparison")

plt.tight_layout()

plt.savefig(
    "final_bar_coverage.png",
    dpi=300,
    bbox_inches="tight"
)
