#!/bin/zsh
# Compare speculative configs on the file-rewrite workload (output mostly copies the input).
cd ${0:A:h}
for spec in draft-dflash draft-dflash,ngram-mod; do
  ./relaunch.sh SPEC=$spec >/dev/null || exit 1
  echo "== SPEC=$spec"
  BENCH_TOKENS=1500 python3 bench.py edit | tail -4
done
