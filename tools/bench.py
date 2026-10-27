"""Throughput benchmark against a running llama-server.

  bench.py decode            short coding prompts: decode t/s + draft acceptance
  bench.py prefill 4k 16k    cold prefill speed at those prompt sizes
  bench.py depth 32k 128k    decode speed *after* a prefix of that size is cached
  bench.py edit              "rewrite this file with a small change" (output mostly copies the input)
"""
import os
import sys
import time

import llm

PROMPTS = [
    "Write a Python function that parses an ISO-8601 duration string like 'P3DT4H5M' into a timedelta. Include tests.",
    "Implement an LRU cache in Rust with O(1) get/put, no external crates. Explain the borrow-checker choices briefly.",
    "Here is a bug: a Go HTTP handler leaks goroutines when the client disconnects mid-stream. Show a minimal example and the fix.",
    "Refactor this into small functions and add type hints:\n\ndef f(d):\n    r=[]\n    for k in d:\n        if d[k]>0:\n            r.append((k,d[k]*2))\n    r.sort(key=lambda x:x[1])\n    return r",
    "Write a bash script that finds the 10 largest files under a directory, ignoring .git, and prints human-readable sizes.",
]


def size(s):
    return int(float(s[:-1]) * 1024) if s.endswith("k") else int(s)


def decode(strength):
    rows = []
    for p in PROMPTS[: int(os.environ.get("BENCH_PROMPTS", len(PROMPTS)))]:
        r = llm.chat([{"role": "user", "content": p}], max_tokens=int(os.environ.get("BENCH_TOKENS", 1024)), strength=strength)
        t = llm.timings(r)
        print(llm.fmt(t), flush=True)
        rows.append(t)
    gen = sum(t["gen_n"] for t in rows)
    secs = sum(t["gen_n"] / t["decode_tps"] for t in rows)
    acc = [t["accept"] for t in rows if t["accept"] is not None]
    print(f"\nMEAN decode {gen / secs:.1f} t/s" + (f", accept {sum(acc) / len(acc):.2f}" if acc else ""))


def edit(strength):
    import glob, sysconfig
    root = sysconfig.get_paths()["stdlib"] + "/"
    pick = [f for f in sorted(glob.glob(root + "*.py")) if 4000 < len(open(f, encoding="utf-8").read()) < 7000][:3]
    rows = []
    for f in pick:
        code = open(f, encoding="utf-8").read()
        msg = f"Rewrite this whole Python file with type hints added to every function signature. Output only the complete file.\n\n```python\n{code}\n```"
        r = llm.chat([{"role": "user", "content": msg}], max_tokens=int(os.environ.get("BENCH_TOKENS", 2500)), strength=strength)
        t = llm.timings(r)
        print(os.path.basename(f), llm.fmt(t), flush=True)
        rows.append(t)
    gen = sum(t["gen_n"] for t in rows)
    secs = sum(t["gen_n"] / t["decode_tps"] for t in rows)
    print(f"\nMEAN edit decode {gen / secs:.1f} t/s")


def prefill(sizes):
    for n in sizes:
        text, tot = llm.code_corpus(n)
        msg = [{"role": "user", "content": text + "\n\nIn one sentence: what is the first file above?"}]
        t0 = time.time()
        r = llm.chat(msg, max_tokens=16, strength="low")
        print(f"[{n} -> {tot} corpus tok] wall {time.time() - t0:.0f}s |", llm.fmt(llm.timings(r)), flush=True)


def depth(sizes, strength):
    for n in sizes:
        text, _ = llm.code_corpus(n)
        for q in ("List the first three file names above.", "Write a Python one-liner that reverses a string."):
            msg = [{"role": "user", "content": text + "\n\n" + q}]
            r = llm.chat(msg, max_tokens=256, strength=strength)
            print(f"[depth {n}] {q[:30]:30s} |", llm.fmt(llm.timings(r)), flush=True)


if __name__ == "__main__":
    mode, args = sys.argv[1], sys.argv[2:]
    strength = "high"
    if mode == "decode":
        decode(strength)
    elif mode == "edit":
        edit(strength)
    elif mode == "prefill":
        prefill([size(a) for a in args])
    elif mode == "depth":
        depth([size(a) for a in args], strength)
