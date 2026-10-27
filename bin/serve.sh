#!/bin/zsh
# Muse Glimmer 30B on llama.cpp: DFlash 2 + n-gram speculative decoding, 128k (trained) context.
# Every knob can be overridden from the environment, e.g.  DRAFT_N=7 bin/serve.sh
set -eu
ROOT=${0:A:h:h}

TARGET=${TARGET:-$ROOT/models/Muse-Glimmer-30B-KQuant-Dynamic-Q4_K_XL.gguf}
DRAFT=${DRAFT:-$ROOT/models/Muse-Glimmer-30B-DFlash2-Q8_0.gguf}
CTX=${CTX:-131072}               # = trained context of Muse Glimmer; beyond this llama.cpp refuses unless overridden
SLOTS=${SLOTS:-1}                 # context is split across slots; keep 1 so a request gets all of CTX
DRAFT_N=${DRAFT_N:-7}             # tuned on M4 Pro: 5-7 best (1.9x); 15 (the published default) only reaches 1.2x
SPEC=${SPEC:-draft-dflash,ngram-mod}  # ngram-mod adds ~+19% on rewrite-style edits, no regression elsewhere
KV=${KV:-f16}                     # KV cache is only ~1.9 GB at 128k (13 full-attn layers, 2 KV heads); quantizing it buys nothing
STRENGTH=${STRENGTH:-high}        # low | medium | high | xhigh (thinking cannot be disabled)
THINK_BUDGET=${THINK_BUDGET:--1}  # hard cap on thinking tokens, -1 = unlimited
UBATCH=${UBATCH:-1024}
CACHE_RAM=${CACHE_RAM:-12288}     # MiB of host RAM for saved prompt caches / checkpoints
PORT=${PORT:-8080}
EXTRA=${EXTRA:-}                  # extra llama-server args, e.g. EXTRA="--presence-penalty 0.3"

SPEC_ARGS=()
if [[ $SPEC != none ]]; then
  SPEC_ARGS=(--spec-type "$SPEC" --spec-draft-n-max "$DRAFT_N")
  [[ $SPEC == *dflash* ]] && SPEC_ARGS+=(-md "$DRAFT" -ngld 99)
fi

# llama.cpp caps the slot at the trained length; only lift that cap if CTX is explicitly set higher
CTX_ARGS=()
(( CTX > 131072 )) && CTX_ARGS=(--override-kv "muse-glimmer.context_length=int:$CTX")

exec caffeinate -i llama-server \
  -m "$TARGET" -ngl 99 "${SPEC_ARGS[@]}" \
  -a muse-glimmer \
  -c "$CTX" -np "$SLOTS" -fa on -ctk "$KV" -ctv "$KV" \
  "${CTX_ARGS[@]}" -b 2048 -ub "$UBATCH" \
  --ctx-checkpoints 64 --checkpoint-min-step 1024 --cache-ram "$CACHE_RAM" \
  --jinja --chat-template-kwargs "{\"reasoning_strength\":\"$STRENGTH\"}" \
  --reasoning-budget "$THINK_BUDGET" \
  --temp 1.0 --top-p 0.95 --top-k 64 \
  --host 127.0.0.1 --port "$PORT" --metrics \
  ${=EXTRA}
