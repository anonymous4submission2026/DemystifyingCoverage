# Demystifying Coverage-Guided Compiler Fuzzing

This repository contains the data and analysis scripts for the paper **"Demystifying Coverage-Guided Compiler Fuzzing"**. The artifact is organized by the paper's three research questions (`rq1`, `rq2`, `rq3`). Each directory contains the raw data and the plotting/analysis scripts needed to reproduce the corresponding figures and results.

---

## Repository Structure

```
rq1/   Coverage configuration analysis — bug detection across compiler pipeline layers
rq2/   Sequential vs. bulk execution — performance and scalability measurements
rq3/   Crash analysis — fuzzing campaign data and crash deduplication scripts
```

---

## Requirements

Install Python dependencies before running any script:

```bash
pip install matplotlib pandas numpy scipy upsetplot
```

All scripts target **Python 3.8+** and produce output as PNG figures or CSV files.

---

## RQ1 — Effect of Coverage Layer Configuration on Bug Detection

**Research question:** How does restricting coverage instrumentation to specific compiler pipeline layers (lexer, parser, type-checker, IR generation, optimizer, code generation) affect the bugs found?

**Data:** `rq1/*.json` — one file per configuration (e.g., `allcov.json` for full instrumentation, `allcov-lexer.json` for all layers except the lexer, through to `allcov-lexer-parser-typechecker-irgen-opt-codegen.json` which corresponds to no coverage). Each file contains unique bug identifiers (`hashcode`) and tracebacks for GCC and Clang/LLVM. File-to-layer mappings are in `rq1/file_to_layer_mappings/`.

**Reproduce figures:**

```bash
# UpSet plot: bug overlap across configurations (Figure X)
python3 rq1/scripts/upset_plot.py rq1/ --out upset.png

# Scatter plot: time-to-first-find vs. total bugs found (Figure X)
python3 rq1/scripts/scatter_time_vs_bugs.py

# Bar chart: per-layer coverage breakdown for GCC and LLVM (Figure X)
python3 rq1/scripts/bar_layer_cov.py
```

---

## RQ2 — Sequential vs. Bulk Compilation Performance

**Research question:** Does batching test-case compilation (bulk mode) improve throughput and reduce overhead compared to sequential execution?

**Data:** `rq2/seq_vs_bulk.csv`, measurements across GCC and Clang, sequential and bulk modes, 1–8 cores, and batch sizes of 5, 25, 50, and 75. Columns: `mode, compiler, trial, cores, batch_size, repetition, wall_time_s, peak_rss_mb`.

**Reproduce figures:**

```bash
# Must be run from the rq2/ directory (script reads results.csv from CWD)
cd rq2
cp seq_vs_bulk.csv results.csv
python3 scripts/plot.py
```

---

## RQ3 — Compiler Crash Analysis

**Research question:** How many distinct crashes (by unique traceback) does the fuzzer find, and how are they distributed across compilers and fuzzing modes?

**Data:** `rq3/Crashes.csv` — 56 confirmed crashes (39 Clang/LLVM, 17 GCC) with columns `Compiler, Issue#`.

**Crash deduplication scripts** (used during the fuzzing campaigns; require the MetaMut fuzzer runtime):

```bash
# Check a crash log and emit per-crash JSON records
python3 rq3/scripts/CrashCheck.py <crash.log> --output <out_dir> --log-mode

# Group crashes by normalized traceback into organized_crashes.json
# Run from inside a fuzzing output directory
python3 rq3/scripts/crash_organizer.py
```

**HPC job scripts** (SLURM; paths hardcoded to `/home/username/` — update before use):

```bash
rq3/scripts/metamut_submit_jobs.sh    # submit fuzzing jobs
rq3/scripts/metamut_run.sh            # single-job entry point
rq3/scripts/run_crash_analysis.sh     # run CrashCheck across all output dirs
rq3/scripts/collect_results.sh        # aggregate crash counts into CSV
```

---

## Notes

- The MetaMut fuzzer source (required by `CrashCheck.py`) is not included in this repository. The pre-collected crash data in `rq3/Crashes.csv` is self-contained and sufficient to review the RQ3 results.
- An archived version of the full artifact (including fuzzer binaries and raw fuzzing outputs) will be submitted upon paper acceptance.
