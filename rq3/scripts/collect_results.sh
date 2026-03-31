#!/bin/bash

# Base directory
BASE_DIR="/home/username/MetaMut/outputs/"
TIME="24h" 
DATE="2025-11-25"

# Output CSV file
OUTPUT_CSV="crash_data_${TIME}.csv"

# Write CSV header
echo "compiler, run,i ssue_number,num_c_files,num_crashes" > "$OUTPUT_CSV"

for THREAD in {0..3}; do
  for compiler in gcc clang; do
    for MODE in bulk cd ce; do
        for RUN in {1..5}; do
                # Construct the directory path
                #DIR="${BASE_DIR}/${issue_type}-issue-8h-${i}"
                DIR="$BASE_DIR/${compiler}-${DATE}-${TIME}-${MODE}/run-${RUN}/thread_${THREAD}"
                echo "${DIR}"
                # Check if directory exists
                if [ ! -d "$DIR" ]; then
                    echo "Directory not found: $DIR"
                    continue
                fi
        
                # Count .c files in default_mutants_folder/
                MUTANTS_DIR="${DIR}/"

                if [ -d "${MUTANTS_DIR}" ]; then
                    NUM_C_FILES=$(find "$MUTANTS_DIR" -name "*.c" -type f | wc -l)
                    echo "NUMBER OF C FILES ==== > ${NUM_C_FILES}"
                else
                    echo "Mutants directory not found: $MUTANTS_DIR"
                    NUM_C_FILES=0
                fi
        
                # Generate organized_crashes.json and count tracebacks
                cd "$DIR"
                python3 /home/username/FastMut/scripts/crash_organizer.py
                
                CRASHES_FILE="${MUTANTS_DIR}/organized_crashes.json"
                if [ -f "$CRASHES_FILE" ]; then
                    NUM_CRASHES=$(grep -o "traceback" "$CRASHES_FILE" | wc -l)
                else
                    echo "Crashes file not found: $CRASHES_FILE"
                    NUM_CRASHES=0
                fi
        
                cd ../..
                
                # Write to CSV
                echo "${compiler}, ${mode}, ${RUN}, ${NUM_C_FILES},${NUM_CRASHES}" >> "$OUTPUT_CSV"
                
                echo "${compiler}, ${A}-bulk, ${B}-mapping, 2h, ${RUN}, - C files: ${NUM_C_FILES}, Crashes: ${NUM_CRASHES}"
                ##sleep 5
    # done
    # done
    done
    done
    done
    done
cd - > /dev/null
echo "Data collection complete. Results saved to $OUTPUT_CSV"