#!/bin/zsh
# Sweep the DFlash draft length; "none" = plain autoregressive baseline.
# Reports decode t/s + draft acceptance for each setting.
cd ${0:A:h}
for n in "$@"; do
  if [[ $n == none ]]; then ./relaunch.sh SPEC=none >/dev/null || exit 1
  else ./relaunch.sh SPEC=draft-dflash DRAFT_N=$n >/dev/null || exit 1; fi
  echo "== DRAFT_N=$n"
  BENCH_TOKENS=512 BENCH_PROMPTS=4 python3 bench.py decode | tail -1
done
