#!/usr/bin/env python3
"""Sequential warm single-stream probe: 3 requests, per-variant."""
import sys, importlib.util, time

spec = importlib.util.spec_from_file_location("lt", "/opt/data/tmp/mtp_loadtest.py")
# loadtest runs its main block on import; guard by reading source up to the driver prints
src = open("/opt/data/tmp/mtp_loadtest.py").read().split('print(f"model={MODEL}')[0]
sys.argv = ["probe", sys.argv[1], "4", "300"]
ns = {"__name__": "probe"}
exec(compile(src, "loadtest_lib", "exec"), ns)

stream_request, results = ns["stream_request"], ns["results"]
for i in range(3):
    stream_request(i)
    r = results[-1]
    print(f"req{i}: ttft={r['ttft']}s tok/s={r['tok_s']} total={r['total_s']}s completion_tokens={r['completion_tokens']}")
