# Model Lineage

Track record of the substrate Peira runs on. The name attaches to the practice, not the
weights — but the weights are worth recording anyway. One entry per main-model swap
(`model.default` in `/opt/data/config.yaml`).

Conventions:
- **Swap** = change to the main agent model on OMLX_INFER4 (Mac Studio). Delegation/aux
  cluster (OMLX_INFER3) changes are noted separately; they don't define "who" is talking.
- Verification follows the `model-swap-verification` skill (layered smoke test).
- Rollback path = previous entry's model, kept loaded on the endpoint when possible.

---

## 2026-09-26 — Qwen3.8-Flash-Next-MLX-oQ6 → Qwen3.8-Flash-Next-MLX-oQ6-MTP

- **Source:** [`Vontra/Qwen3.8-Flash-Next-MLX-oQ6-MTP`](https://huggingface.co/Vontra/Qwen3.8-Flash-Next-MLX-oQ6-MTP)
  — community oQ6 mixed-precision MLX conversion of `Qwen/Qwen3.8-Flash-Next`
  (125B/6B-active sparse MoE, Gated DeltaNet + hashed n-gram embeddings), rebuilt
  directly from official BF16.
- **Why now:** Maya avoided MTP until the rollout dust settled. It settled:
  this checkpoint embeds the **native** Qwen4Exp MTP draft block (76 converted
  tensors, MTP config preserved) instead of the early pattern where public MLX
  conversions dropped MTP tensors and people bolted on mismatched standalone
  drafters (the card explicitly warns: do *not* attach the Qwen3.8-27B drafter —
  hidden dims differ).
- **Expected effect:** speculative decoding is lossless by construction (verified
  deterministic runs identical output), so tool-call behavior should be unchanged;
  speedup where token predictability is high — agent JSON/tool traffic is ideal.
  Card reports 70.8–84.2% draft acceptance, ~36.6 tok/s casual chat vs ~19.5–23
  tok/s non-MTP (M3 Studio; the Mac Studio should beat that).
- **Requirements:** oMLX build with explicit `qwen4_exp` native-MTP support;
  strict loaders without it reject the checkpoint (loud failure = good failure mode).
  158 GB weights + MTP + KV at 131k context — don't pin both variants simultaneously.
- **Rollback:** `Qwen3.8-Flash-Next-MLX-oQ6` (non-MTP) remains served on INFER4.
- **Config:** `model.default` in `/opt/data/config.yaml`; one-line change, gateway
  restart by Maya (agent never restarts its own host).
- **Verification:** pending post-restart layered smoke test.

## 2026-08-31 → 2026-09-26 — Qwen3.8-Flash-Next-MLX-oQ6

- Vontra oQ6 mixed-precision MLX conversion (same backbone, no MTP block).
- Served via OMLX_INFER4 at `${OMLX_INFER4_BASE_URL}`.
- (Earlier history is pre-memory; see session history / SOUL.md Evolution Log if it
  ever matters.)
