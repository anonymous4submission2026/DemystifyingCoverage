#!/bin/bash

SEEDS=(
34
63
15
78
345
22
100
124
887
392193
)

TIME="86399"

mode=(
    "coverageDisabled"
    "coverageEnabled"
    "bulk"

)

for i in {1..1}; do
    sbatch run.sh "${SEEDS[i]}" "${TIME}" "${i}" "0" 
    sbatch run.sh "${SEEDS[i]}" "${TIME}" "${i}" "1" 
    sbatch run.sh "${SEEDS[i]}" "${TIME}" "${i}" "100"
done