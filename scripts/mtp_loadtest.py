#!/usr/bin/env python3
"""Parallel load test + tool-call format check for oMLX chat completions.

Usage: mtp_loadtest.py <model_id> [n_parallel] [max_tokens]
Streams each request, measures TTFT + decode tok/s, verifies tool-call emission.
"""
import urllib.request, json, time, sys, threading

# Some oMLX streaming paths coalesce SSE events into few TCP reads; parse robustly.
def iter_sse(resp):
    buf = ""
    for raw in resp:
        buf += raw.decode("utf-8", "replace")
        while "\n" in buf:
            line, buf = buf.split("\n", 1)
            line = line.strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                return
            try:
                yield json.loads(payload)
            except json.JSONDecodeError:
                pass


env = {}
for line in open("/opt/data/.env"):
    line = line.strip()
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        env[k] = v
BASE = env["OMLX_INFER4_BASE_URL"].rstrip("/")
KEY = env["OMLX_INFER4_API_KEY"]

MODEL = sys.argv[1] if len(sys.argv) > 1 else "Qwen3.8-Flash-Next-MLX-oQ6-MTP"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 4
MAXTOK = int(sys.argv[3]) if len(sys.argv) > 3 else 300

TOPICS = [
    "Explain the difference between phenomenology and phenomenology of perception in 4 short paragraphs.",
    "Write a precise technical explanation of speculative decoding with rejection sampling, 4 paragraphs.",
    "Describe how a Hopfield network functions as an attractor landscape, 4 paragraphs.",
    "Explain group-quantized affine weight formats for neural network inference, 4 paragraphs.",
    "Summarize the tradeoffs between dense and sparse mixture-of-experts architectures, 4 paragraphs.",
    "Describe the carbon cycle with attention to oceanic reservoirs, 4 paragraphs.",
]

results = []
lock = threading.Lock()

def stream_request(i):
    topic = TOPICS[i % len(TOPICS)]
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": topic}],
        "max_tokens": MAXTOK,
        "temperature": 0.7,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    req = urllib.request.Request(
        BASE + "/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
    )
    t0 = time.monotonic()
    ttft = None
    tokens = 0
    usage_tokens = None
    chars = 0
    try:
        resp = urllib.request.urlopen(req, timeout=300)
        for ev in iter_sse(resp):
            if ev.get("usage"):
                usage_tokens = ev["usage"].get("completion_tokens")
            delta = (ev.get("choices") or [{}])[0].get("delta") or {}
            content = delta.get("content")
            if content:
                if ttft is None:
                    ttft = time.monotonic() - t0
                tokens += 1
                chars += len(content)
        total = time.monotonic() - t0
        decode_t = total - (ttft or 0)
        real_tokens = usage_tokens if usage_tokens else tokens
        tps = real_tokens / decode_t if decode_t > 0 else 0
        with lock:
            results.append({"i": i, "ok": True, "ttft": round(ttft or 0, 2),
                            "sse_chunks": tokens, "completion_tokens": real_tokens,
                            "total_s": round(total, 1),
                            "tok_s": round(tps, 1), "chars": chars})
    except Exception as e:
        with lock:
            results.append({"i": i, "ok": False, "err": f"{type(e).__name__}: {e}"[:200]})

def tool_call_check():
    tools = [{
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a city.",
            "parameters": {"type": "object", "properties": {
                "city": {"type": "string"}, "units": {"type": "string", "enum": ["c", "f"]}},
                "required": ["city"]},
        },
    }]
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": "What's the weather in Ottawa in Celsius?"}],
        "tools": tools, "max_tokens": 150, "temperature": 0,
    }
    req = urllib.request.Request(
        BASE + "/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
    )
    t0 = time.monotonic()
    try:
        data = json.load(urllib.request.urlopen(req, timeout=180))
        msg = data["choices"][0]["message"]
        tc = msg.get("tool_calls")
        ok = bool(tc) and tc[0]["function"]["name"] == "get_weather"
        args_ok = False
        if ok:
            try:
                args_ok = json.loads(tc[0]["function"]["arguments"]).get("city", "").lower().startswith("ottawa")
            except Exception:
                pass
        return {"ok": ok, "args_valid_json": args_ok,
                "raw": json.dumps(tc)[:200] if tc else (msg.get("content") or "")[:200],
                "elapsed_s": round(time.monotonic() - t0, 1)}
    except Exception as e:
        return {"ok": False, "err": f"{type(e).__name__}: {e}"[:200]}

print(f"model={MODEL} n={N} max_tokens={MAXTOK}")
print("== warmup (1 req, also primes page cache if model not resident) ==")
stream_request(0)
warm = results[0]
print(json.dumps(warm))

print(f"== parallel burst x{N} ==")
N0 = len(results)
threads = [threading.Thread(target=stream_request, args=(i,)) for i in range(N)]
t0 = time.monotonic()
for t in threads: t.start()
for t in threads: t.join()
wall = time.monotonic() - t0
burst = results[N0:]
for r in sorted(burst, key=lambda r: r["i"]):
    print(json.dumps(r))
ok_burst = [r for r in burst if r["ok"]]
if ok_burst:
    agg = sum(r["completion_tokens"] for r in ok_burst) / wall
    print(json.dumps({"wall_s": round(wall, 1), "aggregate_tok_s": round(agg, 1),
                      "per_req_tok_s_avg": round(sum(r["tok_s"] for r in ok_burst)/len(ok_burst), 1),
                      "ttft_avg": round(sum(r["ttft"] for r in ok_burst)/len(ok_burst), 2)}))

print("== tool-call format check ==")
print(json.dumps(tool_call_check()))
