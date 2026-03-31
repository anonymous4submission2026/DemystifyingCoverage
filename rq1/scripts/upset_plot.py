#!/usr/bin/env python3

import json
import sys
import argparse
from pathlib import Path


CONFIG_ORDER = [
    "allcov",
    "allcov-lexer",
    "allcov-lexer-parser",
    "allcov-lexer-parser-typechecker",
    "allcov-lexer-parser-typechecker-irgen",
    "allcov-lexer-parser-typechecker-irgen-opt",
    "allcov-lexer-parser-typechecker-irgen-opt-codegen",
]

LABEL_OVERRIDE = {
    "allcov-lexer-parser-typechecker-irgen-opt-codegen": "nocov",
}

# ── compact fonts ────────────────────────────────────────────────────────────
FONT_SIZE        = 14
AXIS_LABEL_SIZE  = 14
TITLE_SIZE       = 16
COUNT_LABEL_SIZE = 14

TOP_K = 15   # ensures consistent width across LLVM & GCC


def sort_key(p: Path) -> int:
    try:
        return CONFIG_ORDER.index(p.stem)
    except ValueError:
        return len(CONFIG_ORDER)

def load_hashcodes(json_path: Path, family: str) -> set:
    with open(json_path) as f:
        data = json.loads(f.read(), strict=False)

    entries = data.get(family, [])
    return {e.get("hashcode") for e in entries if e.get("hashcode")}


# ─────────────────────────────────────────────────────────────────────────────
# Render one UpSet plot as image (scale-aligned)
# ─────────────────────────────────────────────────────────────────────────────
def render_upset_image(sets, labels, family, dpi=300):
    import matplotlib.pyplot as plt
    from upsetplot import UpSet, from_contents
    import numpy as np
    import matplotlib as mpl

    mpl.rcParams.update({
        "font.size": FONT_SIZE,
        "axes.titlesize": TITLE_SIZE,
        "axes.labelsize": AXIS_LABEL_SIZE,
    })

    contents = {label: s for label, s in zip(labels, sets)}
    data = from_contents(contents)

    # fig = plt.figure(figsize=(12, 8), dpi=dpi)
    fig = plt.figure(figsize=(24, 14), dpi=dpi)

    upset = UpSet(
        data,
        subset_size="count",
        show_counts=True,
        sort_by="cardinality",
        sort_categories_by=None,
        element_size=18,
        intersection_plot_elements=TOP_K,
    )

    ax_dict = upset.plot(fig)

    ax_dict["intersections"].set_title(
        f"{family.upper()} ({len(data)} bugs)",
        fontsize=TITLE_SIZE,
        pad=10,
    )

    # get current positions
    pos_int = ax_dict["intersections"].get_position()
    pos_mat = ax_dict["matrix"].get_position()
    pos_tot = ax_dict["totals"].get_position()

    # rebalance heights (no overlap)
    shrink = 0.9   # intersections shrink
    grow   = 1.25   # matrix grow

    # intersections (top)
    ax_dict["intersections"].set_position([
        pos_int.x0,
        pos_int.y0 + (pos_int.height * (1 - shrink)),  # shift up slightly
        pos_int.width,
        pos_int.height
    ])

    # matrix (middle)
    ax_dict["matrix"].set_position([
        pos_mat.x0,
        pos_mat.y0,
        pos_mat.width,
        pos_mat.height * grow
    ])

    # totals (bottom) → keep aligned
    ax_dict["totals"].set_position([
        pos_tot.x0,
        pos_tot.y0,
        pos_tot.width,
        pos_tot.height * grow
    ])

    ax_dict["intersections"].set_ylabel("Intersection size", fontsize=AXIS_LABEL_SIZE)
    ax_dict["totals"].set_xlabel("Total bugs", fontsize=AXIS_LABEL_SIZE)

    # smaller count labels
    for ax_name in ("intersections", "totals"):
        for txt in ax_dict[ax_name].texts:
            txt.set_fontsize(COUNT_LABEL_SIZE)

    # normalize layout anchor
    for ax in ax_dict.values():
        ax.set_anchor('C')

    for p in ax_dict["matrix"].patches:
        p.set_visible(False)

    # convert figure → image
    fig.canvas.draw()
    img = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
    img = img.reshape(fig.canvas.get_width_height()[::-1] + (3,))

    plt.close(fig)
    return img

def crop_left_whitespace(img, threshold=250):
    import numpy as np

    gray = img.mean(axis=2)

    # find first column that is not almost white
    cols = np.where(gray < threshold)[1]

    if len(cols) == 0:
        return img

    left = cols.min()
    return img[:, left:]


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("json_dir")
    parser.add_argument("--out", default="combined_upset.png")
    args = parser.parse_args()

    json_dir = Path(args.json_dir)
    input_paths = sorted(json_dir.glob("*.json"), key=sort_key)

    if not input_paths:
        print("No JSON files found", file=sys.stderr)
        sys.exit(1)

    # original labels
    original_labels = [LABEL_OVERRIDE.get(p.stem, p.stem) for p in input_paths]

    # short labels
    labels = [f"C{i+1}" for i in range(len(original_labels))]

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    DPI = 300

    # ── load sets ────────────────────────────────────────────────────────────
    sets_llvm = [load_hashcodes(p, "llvm") for p in input_paths]
    sets_gcc  = [load_hashcodes(p, "gcc") for p in input_paths]

    # ── render both plots with identical scale ───────────────────────────────
    img_llvm = render_upset_image(sets_llvm, labels, "clang", dpi=DPI)
    img_gcc  = render_upset_image(sets_gcc, labels, "gcc", dpi=DPI)

    img_llvm = crop_left_whitespace(
        render_upset_image(sets_llvm, labels, "clang", dpi=DPI)
    )
    img_gcc = crop_left_whitespace(
        render_upset_image(sets_gcc, labels, "gcc", dpi=DPI)
    )

    # ── combine side-by-side (FIXED SPACING HERE) ─────────────────────────────
    fig, axes = plt.subplots(
        1, 2,
        # figsize=(16, 6),
        figsize=(20, 8),
        dpi=DPI,
        gridspec_kw={"wspace": -0.7}
    )

    axes[0].imshow(img_llvm)
    axes[0].axis("off")

    axes[1].imshow(img_gcc)
    axes[1].axis("off")

    # ensure centered anchoring (optional but helps alignment)
    for ax in axes:
        ax.set_anchor('C')

    # ── shared legend ────────────────────────────────────────────────────────
    legend_labels = [
        f"{short} = {orig}"
        for short, orig in zip(labels, original_labels)
    ]

    handles = [
        Line2D([0], [0], marker='o', linestyle='', color='black', markersize=3)
        for _ in legend_labels
    ]

    fig.legend(
        handles,
        legend_labels,
        loc="lower center",
        bbox_to_anchor=(0.48, -0.09),
        ncol=2,
        frameon=True,
        fontsize=17,
        handletextpad=0.3,
        columnspacing=0.6,
        borderpad=0.2,
        labelspacing=0.2,
        handlelength=0.8,
    )

    # adjust bottom for legend (keep) + optionally tweak wspace again
    fig.subplots_adjust(
        left=0.0,
        right=1.0,
        top=1.0,
        bottom=0.1,
        wspace=0.0
    )

    fig.savefig(args.out, dpi=DPI, bbox_inches="tight")
    print(f"Saved {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()


    