"""Death-loop detector: run loop-prone prompts and flag degenerate repetition.

  loopcheck.py [--max-tokens 4000] [--repeat 1] [--only name,name]

A run is flagged LOOP when it hit the token limit AND the tail of its reasoning
or answer is dominated by repeated word-6-grams (healthy prose/code: < 0.3).
"""
import argparse
import sys
import time

import llm

SUDOKU = """Solve this sudoku (0 = empty) and print the completed grid:
800000000
003600000
070090200
050007000
000045700
000100030
001000068
008500010
090000400"""

PROMPTS = {
    "proof+code": "Prove that there are infinitely many primes p with p ≡ 3 (mod 4). Then write a Python sieve that verifies the claim numerically up to 10**6.",
    "lockfree": "Design a lock-free bounded MPMC queue in C++20. Give complete code and justify every memory_order you chose.",
    "pow2-table": "Write a markdown table of 2^0 through 2^100 with columns: exponent, exact decimal value, number of digits.",
    "boilerplate": "Write a Python module with 20 dataclasses modelling a hotel-booking domain. Each needs 6 typed fields, a validate() method and a to_dict() method.",
    "sudoku": SUDOKU,
    "bugfind": "This function is supposed to merge overlapping intervals but fails on some inputs. Find ALL bugs and give a corrected version with tests.\n\n```python\ndef merge(iv):\n    iv.sort()\n    out=[iv[0]]\n    for a,b in iv[1:]:\n        if a<out[-1][1]:\n            out[-1][1]=max(out[-1][1],b)\n        else:\n            out.append([a,b])\n    return out\n```",
    "regex-hell": "Write a regex that validates RFC 5322 email addresses completely, and explain every group. Then list 30 tricky valid and 30 tricky invalid examples with reasons.",
    "refactor-plan": "I have a 40k-line Django monolith with circular imports between 12 apps. Give a concrete, ordered, step-by-step plan to untangle it, including the exact commands and scripts you would run at each step.",
}

LONG_CTX_QUESTIONS = [
    "Which file defines the most classes? Think carefully and list the top 3 with class counts.",
    "Pick the three most complex functions across all files above by your own judgement, explain why, and sketch a refactor for each.",
]


def dup_fraction(text, n=6, tail_words=700):
    w = text.split()[-tail_words:]
    if len(w) < 50:
        return 0.0
    sh = [tuple(w[i:i + n]) for i in range(len(w) - n)]
    return 1 - len(set(sh)) / len(sh)


def run(name, messages, max_tokens, strength):
    t0 = time.time()
    r = llm.chat(messages, max_tokens=max_tokens, strength=strength)
    m = r["choices"][0]["message"]
    reasoning, content = m.get("reasoning_content") or "", m.get("content") or ""
    fin = r["choices"][0]["finish_reason"]
    dr, dc = dup_fraction(reasoning), dup_fraction(content)
    loop = fin == "length" and max(dr, dc) > 0.5
    t = llm.timings(r)
    print(f"{'LOOP' if loop else 'ok  '} {name:14s} finish={fin:6s} gen={t['gen_n']:5d} "
          f"dup(reason)={dr:.2f} dup(answer)={dc:.2f} {t['decode_tps'] or 0:4.1f} t/s {time.time() - t0:4.0f}s", flush=True)
    if loop:
        tail = (reasoning if dr >= dc else content)[-300:].replace("\n", " ")
        print(f"       tail: ...{tail}", flush=True)
    return loop


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-tokens", type=int, default=4000)
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--only", default="")
    ap.add_argument("--strength", default="high")
    ap.add_argument("--long-ctx", type=int, default=0, help="also ask questions over a code corpus of this many tokens")
    a = ap.parse_args()
    only = set(filter(None, a.only.split(",")))
    jobs = [(k, [{"role": "user", "content": v}]) for k, v in PROMPTS.items() if not only or k in only]
    if a.long_ctx:
        corpus, _ = llm.code_corpus(a.long_ctx)
        jobs += [(f"longctx-{i}", [{"role": "user", "content": corpus + "\n\n" + q}]) for i, q in enumerate(LONG_CTX_QUESTIONS)]
    loops = total = 0
    for _ in range(a.repeat):
        for name, msgs in jobs:
            loops += run(name, msgs, a.max_tokens, a.strength)
            total += 1
    print(f"\nLOOPS: {loops}/{total}")
    sys.exit(1 if loops else 0)


if __name__ == "__main__":
    main()
