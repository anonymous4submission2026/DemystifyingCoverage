
#!/bin/bash

BASE_DIR="/home/username/MetaMut/outputs/"
PYTHON_SCRIPT="/home/username/MetaMut/fuzzer/CrashCheck.py"
TIME="24h"
DATE="2025-11-25"


for THREAD in {0..3}; do
  for compiler in gcc; do
    for MODE in bulk cd ce; do
        for RUN in {1..5}; do
        VARIANT_DIR="$BASE_DIR/${compiler}-${DATE}-${TIME}-${MODE}/run-${RUN}/thread_${THREAD}"
        CRASH_LOG="$VARIANT_DIR/crash.log"
        #TEST_LOG_PATH="/home/username/optimizing-kitten/kitten/experiment/kitten/true-bulk-false-mapping-T1-8h-2/default_mutants_folder/thread_1/crash.log"
        #TEST_OUT_DIR="/home/username/optimizing-kitten/kitten/experiment/kitten/true-bulk-false-mapping-T1-8h-2/default_mutants_folder/thread_1/batch_crash_results"
        OUT_DIR="$VARIANT_DIR/batch_crash_results/"

        #echo "Variant directory: $VARIANT_DIR"
        #echo "Crash log path:    $CRASH_LOG"
        #echo "Output path:       $OUT_DIR"
        #echo "-------------------------------------------"

        #echo "python3 $PYTHON_SCRIPT $CRASH_LOG --output $OUT_DIR --log-mode"

        sbatch -c 2 --wrap="python3 $PYTHON_SCRIPT $CRASH_LOG --output $OUT_DIR --log-mode"
        #sbatch -c 2 --wrap="python3 $PYTHON_SCRIPT '$BASE_DIR/thread_$i/crash.log' --output '$BASE_DIR/thread_$i/batch_crash_results' --log-mode"
        done
    done
  done
done

