# Muse Glimmer 30B, local agentic coding on an M4 Pro (48 GB)

Meta's Muse Glimmer 30B (dense) served by llama.cpp with DFlash 2 + n-gram
speculative decoding, driven by opencode. Context window: 131,072 (the length
the model was trained on).

## Use it

```sh
bin/serve.sh          # start the server (keeps the Mac awake; ~25 GB RAM). Ctrl-C or `pkill llama-server` to stop
opencode              # default model is already muse/muse-glimmer
```

First request of a session pays ~80 s of prefill (opencode's ~9k-token prompt at ~110 tok/s).
After that, turns reuse the cached prefix and only prefill what is new.

## What is installed

| Piece | Choice |
|---|---|
| Engine | llama.cpp 0.7.0 (`brew install llama.cpp`), Metal |
| Target | `Muse-Glimmer-30B-KQuant-Dynamic-Q4_K_XL.gguf` (19.7 GB, Meta's near-lossless build: 0.2% avg degradation) |
| Drafter | `incoai/Muse-Glimmer-30B-DFlash2-GGUF` Q8_0 (3.0 GB) |
| Speculation | `--spec-type draft-dflash,ngram-mod`, 7 drafted tokens |
| Sampler | temp 1.0, top-p 0.95, top-k 64 (Meta's recommendation), reasoning strength `high` |
| Agent | opencode, provider `muse` in `~/.config/opencode/opencode.json` (original saved in `backup/`) |

## Measured on this machine (M4 Pro, nothing else running)

| | tok/s |
|---|---|
| Plain decode, no speculation | 11.3 |
| + DFlash 2, 7 drafted tokens | 21.2 (1.9x) |
| + DFlash 2, 15 drafted tokens (published default) | 13.6 |
| Real agent turns (opencode / Claude Code) | 22-44 |
| Verbatim copy / file rewrite, DFlash 2 + n-gram | 64-68 (5.7x) |
| Prefill | 114 at 4k, 103 at 33k |

Why 7 and not 15 drafted tokens: speed falls off a cliff above 8 verified tokens
per step (21 -> 15 tok/s at 10). The M4 Pro's GPU cannot verify a 16-token block
cheaply, unlike the H200 the published numbers come from.

Loop check (`tools/loopcheck.py`): 0 of 8 loop-prone prompts (proof, lock-free
queue, 100-row table, boilerplate, sudoku, bug hunt, regex, refactor plan) looped
at 3500 tokens, repeated-text score 0.00-0.06 (flag threshold 0.5). Two full agent
runs (Claude Code, opencode) fixed a small bug in a scratch repo in 8-9 turns without
looping. That is evidence, not a guarantee, and says nothing about multi-hour sessions
or tasks near the 128k limit.

## Decisions worth knowing

- **131,072 context, not 200k.** The model is trained to 131,072. llama.cpp clamps to
  that unless you override the GGUF metadata, and nothing was verified past it.
  `CTX=200000 bin/serve.sh` applies the override at your own risk.
- **No KV cache quantization.** Only 13 of 52 layers use full attention (the rest are
  2048-token sliding windows) and there are 2 KV heads, so the f16 cache is ~1.9 GB at
  128k. Quantizing it would save ~1 GB and cost quality.
- **No MTP.** Muse Glimmer has no MTP head (`num_nextn_predict_layers` is absent). DFlash 2 is its
  speculative decoder.
- **Single slot.** Context is divided across slots, so `-np 1` gives a request the full window.
  Subagents therefore run one at a time.
- **Thinking cannot be turned off**, only its strength (`STRENGTH=low|medium|high|xhigh`).
  `THINK_BUDGET=N` hard-caps thinking tokens if you ever see a runaway.

## Knobs (environment variables for `bin/serve.sh`)

`CTX` `DRAFT_N` `SPEC` `KV` `STRENGTH` `THINK_BUDGET` `UBATCH` `CACHE_RAM` `PORT` `EXTRA`
(e.g. `EXTRA="--presence-penalty 0.3"` as a loop safety net if one ever shows up).

## Tools (`tools/`)

- `relaunch.sh SPEC=none DRAFT_N=5 ...` restart the server with overrides and wait until healthy
- `bench.py decode | prefill 4k 16k | depth 32k | edit` throughput and draft acceptance
- `sweep_n.sh none 3 5 7 10` draft-length sweep; `spec_compare.sh` speculative-config comparison
- `loopcheck.py [--max-tokens N] [--long-ctx 30000]` death-loop detector

## Gotchas

- opencode 2.1.4 silently hangs if any field of a provider fails validation (it drops the
  whole provider and `opencode run` never errors). `chunkTimeout: false` is invalid in v2; use a number.
  Check with `opencode models --standalone --print-logs --log-level warn | grep diagnostic`.
- Do not run games or other GPU work during benchmarks. They halve the numbers.
- The cold-start cost scales with prompt size, so keep AGENTS.md and MCP servers small.
