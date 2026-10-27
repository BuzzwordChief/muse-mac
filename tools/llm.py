"""Tiny stdlib client for llama-server, shared by the bench/test scripts."""
import glob
import json
import os
import sysconfig
import urllib.request

URL = os.environ.get("MUSE_URL", "http://127.0.0.1:8080")


def post(path, body, timeout=7200):
    req = urllib.request.Request(
        URL + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def tokenize(text):
    return post("/tokenize", {"content": text, "add_special": False})["tokens"]


def chat(messages, max_tokens=512, strength=None, **kw):
    body = {"messages": messages, "max_tokens": max_tokens, "stream": False, **kw}
    if strength:
        body["chat_template_kwargs"] = {"reasoning_strength": strength}
    return post("/v1/chat/completions", body)


def code_corpus(target_tokens, skip_tokens=0):
    """Concatenate real source files (python stdlib) until ~target_tokens.

    Deterministic, so repeated calls give an identical prefix (cacheable).
    """
    root = sysconfig.get_paths()["stdlib"] + "/"
    files = sorted(glob.glob(root + "*.py")) + sorted(glob.glob(root + "*/*.py"))
    out, total = [], 0
    for f in files:
        try:
            text = open(f, encoding="utf-8").read()
        except (UnicodeDecodeError, OSError):
            continue
        if not 2000 < len(text) < 60000:
            continue
        n = len(tokenize(text))
        if skip_tokens > 0:
            skip_tokens -= n
            continue
        out.append(f"### FILE {os.path.relpath(f, root)}\n{text}\n")
        total += n
        if total >= target_tokens:
            break
    return "".join(out), total


def timings(resp):
    t = resp.get("timings", {})
    dn, da = t.get("draft_n", 0), t.get("draft_n_accepted", 0)
    return {
        "prompt_n": t.get("prompt_n"),
        "cache_n": t.get("cache_n"),
        "prefill_tps": t.get("prompt_per_second"),
        "prefill_s": (t.get("prompt_ms") or 0) / 1000,
        "gen_n": t.get("predicted_n"),
        "decode_tps": t.get("predicted_per_second"),
        "accept": (da / dn) if dn else None,
    }


def fmt(t):
    f = lambda v, p=1: "-" if v is None else f"{v:.{p}f}"
    return (f"prompt={t['prompt_n']} cached={t['cache_n']} prefill={f(t['prefill_tps'])} t/s ({f(t['prefill_s'])}s)"
            f" | gen={t['gen_n']} decode={f(t['decode_tps'])} t/s accept={f(t['accept'], 2)}")
