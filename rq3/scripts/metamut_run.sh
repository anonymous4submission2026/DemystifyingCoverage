#!/bin/bash
#SBATCH --job-name=ce-MetaMut
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=20
#SBATCH --time=24:00:00

seed=$1
TIME=$2
NumerOfRuns=$3
Mode=$4
Compier=$5

python3 /home/username/optimizing-fuzzers/Optimizing-MetaMut/fuzzer/run.py \
    -j 10 \
    --seed "$seed" \
    --repeat-times 10 \
    --duration "${TIME}" \
    --seeds-dir /home/username/optimizing-fuzzers/MetaMut/seeds/ \
    --nor "${NumerOfRuns}" \
    --mode "${Mode}" \
    --wdir "$(pwd)"