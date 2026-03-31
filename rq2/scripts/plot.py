import matplotlib
matplotlib.use("Agg")

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import ttest_ind
from matplotlib.lines import Line2D

plt.rcParams.update({
    "font.size":        15,
    "axes.titlesize":   17,
    "axes.labelsize":   15,
    "xtick.labelsize":  14,
    "ytick.labelsize":  14,
    "legend.fontsize":  15,
})

df = pd.read_csv("results.csv")
df["batch_size"] = pd.to_numeric(df["batch_size"], errors="coerce")

agg = (
    df.groupby(["compiler", "mode", "cores", "batch_size"], dropna=False)
      .agg({
          "wall_time_s": "mean",
          "peak_rss_mb": "mean"
      })
      .reset_index()
)

agg["batch_size"] = agg["batch_size"].fillna(0).astype(int)
agg["mode_order"] = agg["mode"].apply(lambda m: 0 if m == "seq" else 1)
agg = agg.sort_values(by=["cores", "mode_order", "batch_size"])

def make_config(row):
    if row["mode"] == "seq":
        return f"seq-c{row['cores']}"
    else:
        return f"bulk-c{row['cores']}-b{row['batch_size']}"

agg["config"] = agg.apply(make_config, axis=1)

def cohens_d(x, y):
    x = np.array(x)
    y = np.array(y)
    if len(x) < 2 or len(y) < 2:
        return np.nan
    vx = np.var(x, ddof=1)
    vy = np.var(y, ddof=1)
    if vx == 0 and vy == 0:
        return 0.0
    pooled_std = np.sqrt(
        ((len(x)-1)*vx + (len(y)-1)*vy) /
        (len(x)+len(y)-2)
    )
    if pooled_std == 0:
        return np.nan
    return (np.mean(y) - np.mean(x)) / pooled_std

def effect_category(d):
    if np.isnan(d):
        return None
    ad = abs(d)
    if ad < 0.5:
        return "small"
    elif ad < 0.8:
        return "moderate"
    else:
        return "large"

fig, axes = plt.subplots(2, 1, figsize=(20, 10), sharex=False)
compilers = ["clang", "gcc"]
legend_elements = None

print("\n===== EFFECT SIZE REPORT =====\n")

for ax, compiler in zip(axes, compilers):

    sub_plot = agg[agg["compiler"] == compiler].reset_index(drop=True)
    sub_raw  = df[df["compiler"] == compiler]

    configs = sub_plot["config"].tolist()
    memory  = sub_plot["peak_rss_mb"].values

    for (conf, time, mem) in zip(configs, times, memory):
        print(f"{compiler.upper()} {conf}: time={time:.3f}s mem={mem:.1f}MB")

    x_positions = []
    current_x = 0
    previous_core = None
    group_gap = 0.6

    for _, row in sub_plot.iterrows():
        core = row["cores"]
        if previous_core is not None and core != previous_core:
            current_x += group_gap
        x_positions.append(current_x)
        current_x += 1
        previous_core = core

    x_positions = np.array(x_positions)
    pos_map = {i: x_positions[i] for i in range(len(sub_plot))}
    width = 0.4

    bars_time = ax.bar(
        x_positions - width/2, times, width,
        color="blue", label="Wall Time (s)"
    )

    ax2 = ax.twinx()
    bars_mem = ax2.bar(
        x_positions + width/2, memory, width,
        color="orange", label="Peak RSS (MB)"
    )

    ax.set_ylim(0, max(times)  * 1.08)
    ax2.set_ylim(0, max(memory) * 1.08)

    ax.yaxis.set_major_locator(plt.MaxNLocator(nbins=4, prune="both"))
    ax2.yaxis.set_major_locator(plt.MaxNLocator(nbins=4, prune="both"))

    time_offset = (max(times)  - min(times))  * 0.03
    mem_offset  = (max(memory) - min(memory)) * 0.03

    print(f"\n--- {compiler.upper()} ---\n")

    for i, row in sub_plot.iterrows():
        if row["mode"] != "bulk":
            continue

        core  = row["cores"]
        batch = row["batch_size"]

        seq_rows = sub_raw[
            (sub_raw["mode"] == "seq") &
            (sub_raw["cores"] == core)
        ]
        bulk_rows = sub_raw[
            (sub_raw["mode"] == "bulk") &
            (sub_raw["cores"] == core) &
            (sub_raw["batch_size"] == batch)
        ]

        if len(seq_rows) < 2 or len(bulk_rows) < 2:
            continue

        d_time = cohens_d(seq_rows["wall_time_s"], bulk_rows["wall_time_s"])
        _, p_time = ttest_ind(
            seq_rows["wall_time_s"], bulk_rows["wall_time_s"], equal_var=False
        )
        print(f"cores={core} batch={batch} [TIME] d={d_time:.3f} p={p_time:.4f}")

        cat_time = effect_category(d_time)
        if p_time < 0.05 and cat_time:
            xpos = pos_map[i] - width/2
            ypos = row["wall_time_s"] + time_offset
            if cat_time == "small":
                ax.scatter(xpos, ypos, s=70,  marker="s", color="darkgreen")
            elif cat_time == "moderate":
                ax.scatter(xpos, ypos, s=70,  marker="o", color="darkred")
            else:
                ax.scatter(xpos, ypos, s=130, marker="*", color="magenta")

        d_mem = cohens_d(seq_rows["peak_rss_mb"], bulk_rows["peak_rss_mb"])
        _, p_mem = ttest_ind(
            seq_rows["peak_rss_mb"], bulk_rows["peak_rss_mb"], equal_var=False
        )
        print(f"cores={core} batch={batch} [MEM ] d={d_mem:.3f} p={p_mem:.4f}")

        cat_mem = effect_category(d_mem)
        if p_mem < 0.05 and cat_mem:
            xpos = pos_map[i] + width/2
            ypos = row["peak_rss_mb"] + mem_offset
            if cat_mem == "small":
                ax2.scatter(xpos, ypos, s=70,  marker="s", color="darkgreen")
            elif cat_mem == "moderate":
                ax2.scatter(xpos, ypos, s=70,  marker="o", color="darkred")
            else:
                ax2.scatter(xpos, ypos, s=130, marker="*", color="magenta")

    ax.set_title(f"{compiler.upper()} Performance (Averaged)")
    ax.set_ylabel("Wall Time (s)", labelpad=8)
    ax2.set_ylabel("Peak RSS (MB)", labelpad=12)

    ax.set_xticks(x_positions)
    ax.set_xticklabels(configs, rotation=30, ha="right")

    if legend_elements is None:
        legend_elements = [
            bars_time,
            bars_mem,
            Line2D([0], [0], marker='s', color='darkgreen',
                   linestyle='None', markersize=10,
                   label='Small effect (between seq-cX and bulk-cX-bY)'),
            Line2D([0], [0], marker='o', color='darkred',
                   linestyle='None', markersize=10,
                   label='Moderate effect (between seq-cX and bulk-cX-bY)'),
            Line2D([0], [0], marker='*', color='magenta',
                   linestyle='None', markersize=14,
                   label='Large effect (between seq-cX and bulk-cX-bY)'),
        ]

fig.legend(
    handles=legend_elements,
    loc="lower center",
    bbox_to_anchor=(0.5, -0.02),
    ncol=3,
    frameon=True,
    framealpha=0.9,
    edgecolor="grey",
    fontsize=17,
)

plt.tight_layout()
plt.subplots_adjust(bottom=0.20, hspace=0.35)
plt.savefig("bar_seq_vs_bulk.png", dpi=300, bbox_inches="tight")
plt.close(fig)

print("\nSaved plot to bar_seq_vs_bulk.png\n")