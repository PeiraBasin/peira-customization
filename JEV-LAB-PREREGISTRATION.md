# Lab Nervous System — Pre-Registration Protocol (Jev-Lab v0.1)

**Status: DRAFT — awaiting Maya's veto (sent 2026-10-03). No generation-0 compute until sign-off.**

Booked 2026-09-26; woken by cron `6a601f8a278c` on 2026-10-03.

---

## 0. One-paragraph summary

We evolve populations of **Jev-like decision models** (TypeSafe's Jev class: small models that
read a `state` and emit *typed, calibrated probability distributions* over a fixed question
schema in one forward pass — **not** LeCun's JEPA) over lab telemetry. The genome is not a
network from scratch: it is *(question subset × base-clone config × calibration transform)*.
Fitness is the **joint held-out mean log-score above baseline floors** — never calibration
alone, never sharpness alone. Questions are posed at time `t` using only state up to `t` and
scored strictly on the held-out window `(t, t+Δ]`. The experiment asks whether a population of
tiny System-1 reflexes can learn the lab's *relevant signal manifold* — which telemetry
features actually predict the lab's future — cheaper and faster than any generative model
could, and whether evolution finds couplings a human wouldn't think to ask about.

## 1. Hypotheses (pre-registered, checkable)

- **H1 (manifold learnability).** Trained decision models beat both fitness floors
  (base-rate, periodicity) on ≥4 of 10 questions by ≥5% relative skill (Δ mean log-score)
  over a 14-day held-out stream. *Falsified if no model beats both floors on any question
  after 3 generations.*
- **H2 (calibration is the bottleneck, not accuracy).** Top-decile models by *accuracy* are
  measurably overconfident (reliability-curve slope > 1.1) while top-decile by *joint log-score*
  are not — i.e., a naive accuracy-based population would drift to overconfidence. This is the
  core selection-pressure claim.
- **H3 (cheapness floor).** A 0.8B-class clone (Kev) LoRA-tuned on lab telemetry matches or
  beats a zero-training wrapper on a 27B-class base for *this* telemetry domain (near-parity
  on the joint score), despite the Decision Index suggesting base-model breadth otherwise wins.
  Telemetry is a narrow domain; we predict the moat inverts here.

Pre-registered predictions are the point: post-hoc rescues get logged in the Amendment
section (§12), never silently folded into the result.

## 2. What a "Jev-like model" is here (operational definition)

Contract (from the 2026-09-24 ecosystem review, session `@session:default/20260924_115019_f6463d95`):
send a `state` (JSON of lab telemetry snapshot) + typed **questions**, get probability
distributions for all questions in one parallel forward pass. Three primitives:

| primitive | shape | output |
|---|---|---|
| `noul` | yes/no question | calibrated P(true) |
| `choice` | pick 1 of N named options | distribution over options |
| `score` | ordinal rubric 0..K | distribution over ranks |

"Zero hallucination" means *zero schema violations*, not correctness — which is exactly why
the scoring rule (§5) does the real work.

**Ecosystem candidates (from the review):**
1. **`jaredpalmer/kev`** — 0.8B Qwen3.5-based, LoRA + pointer head, Apache-2.0, weights on HF,
   trains ~1h on one H100 (our epochs will be far smaller), MLX-capable. Primary candidate.
2. **`Mapika/decider`** — Qwen3.5 fine-tunes, speaks TypeSafe's wire format, calibration-aware
   RL, most rigorous evals. Second candidate / calibration reference.
3. **Laya** (ModernBERT 421M encoder, Apache-2.0) — cheap CPU-resident floor candidate for
   INFER1's spare cycles; known weakness at high-cardinality choice (Banking77 42.5% vs Jev 87%).
4. Hand-rolled pointer head on a tiny causal base — fallback only if Kev's training loop
   resists our data format.

## 3. The first ten questions (typed, machine-checkable ground truth)

Rules for admission: ground truth must be **mechanically extractable** from the telemetry
store after the window closes, with no human judgment. Δ is fixed per question at registration.
`state(t)` = telemetry snapshot ≤ t only (see leak controls §6).

| # | id | type | question | Δ | ground truth source |
|---|----|------|----------|---|---------------------|
| Q1 | restart-any | noul | Will any container on infer1 exit non-zero in the window? | 1 h | Komodo `ListDockerContainers` diff + docker events |
| Q2 | hermes-up | noul | Is the `hermes` container still running (same container id) at window end? | 6 h | docker inspect |
| Q3 | top-error-svc | choice | Which service emits the most error-level log lines in the window? Options: `hermes, hindsight, firecrawl, supabase, gitlab, synapse, none-most` | 1 h | dozzle log volume (per-service regex count) |
| Q4 | infer2-gpu-busy | noul | Will infer2 GPU util exceed 80% for ≥5 consecutive minutes? | 4 h | nvidia-smi sampler (to be added; see §10) |
| Q5 | disk-growth | score | infer1 `/opt/data` growth in window: 0: <0.5 GB, 1: 0.5–2, 2: 2–10, 3: >10 GB | 24 h | df sampler |
| Q6 | komodo-latency | score | Komodo `/read` p95 probe latency in window: 0: <100ms, 1: <300ms, 2: <1s, 3: ≥1s | 1 h | prober (5-min cadence) |
| Q7 | backup-ok | noul | Do all backup sidecars (hindsight, outline, authentik, komodo) succeed in the window? | 24 h | backup sidecar exit logs |
| Q8 | wake-hour | choice | Next hour's request regime on infer1 (llama-swap + hermes combined req count): `dead (0-2), low (3-20), busy (21-100), spike (>100)` | 1 h | llama-swap + hermes logs |
| Q9 | infer1-hiccup | noul | Will ≥2 *distinct* monitored services fail healthcheck in the window? | 2 h | prober (per-service HTTP/TCP checks, 1-min cadence) |
| Q10 | whale-hour | noul | Will any single llama-swap request on infer1 exceed 120 s? | 4 h | llama-swap access log |

Q3/Q8's option sets are frozen; if telemetry shows an option is never the truth after the
pilot, that is an amendment (§12), not a silent edit.

## 4. Fitness floors (baselines)

Every question gets two floors computed on the **same** held-out windows as the models:

1. **Base-rate predictor** — predicts the empirical marginal (from the *training* split only;
   refit weekly on data ≤ t₀, never on the scored window). For `noul`: constant p = training
   frequency. For `choice`/`score`: training distribution.
2. **Periodicity predictor** — hour-of-day × day-of-week climatology from the training split
   (the "the lab has a circadian rhythm" model).

A model's **skill** on question q = mean log-score(model) − mean log-score(base-rate).
Reproduction fitness = mean skill across the model's question subset, **floored at zero**:
any model below *both* floors on a question contributes zero fitness there and is culled
population-wide after two generations. The floors are not reporting decoration; they gate
mating. (This kills the degenerate "confident on a constant signal" lineage immediately.)

## 5. Scoring rule — the joint only

Primary metric per question: **mean log-score** (strictly proper). We *report* the
Bröcker/Kullback decomposition —

> mean log-score = sharpness − calibration-deficiency

— but **selection and ranking use only the joint**. Decomposition terms are diagnostics
(H2 evidence), never components of the objective. Rationale: rewarding calibration alone
selects for mushy 0.5-everything models; rewarding sharpness alone selects for overconfident
liars; the proper scoring rule is exactly the mechanism that makes the joint the only thing
that pays. Same discipline as RLCD (reinforcement learning with calibration reward ≈
proper-scoring-rule RL per Raschka's reading of Jev), applied at the *evolutionary* level.

Ties between lineages broken by: (1) skill on more distinct questions, (2) smaller param
count, (3) cheaper inference. Cost is a tiebreaker, never in the fitness — we don't want the
population evolving lobotomies to win on price.

## 6. Leak controls

- **Temporal split with embargo.** Question instance posed at t, state = telemetry ≤ t,
  scored on (t, t+Δ]. Embargo = Δ between train and test windows; no training row's state may
  overlap any scored window.
- **Freeze before wake.** Question set, Δs, option sets, scoring code, and split boundaries
  are committed (this document + `jev-lab/` code) *before* generation 0 runs. The commit hash
  is the registration.
- **One-way door on truth.** Ground truth is extracted by a separate scorer script that reads
  only closed windows; the training pipeline physically cannot import it (separate directory,
  read-only mount).
- **No peeking via the population.** Lineages that died are not resurrected with knowledge
  from scored windows; selection uses only training-split validation.
- **Amendment log.** Any change to questions/scoring after registration goes in §12 with
  date, rationale, and a restated (weakened) claim. All results report pre- and post-amendment
  numbers separately.

## 7. Evolutionary setup (generation 0 spec, pending sign-off)

- **Population:** 12 individuals. Genome = (question subset ⊆ {Q1..Q10}, base ∈ {kev-0.8B,
  laya}, LoRA rank ∈ {8, 16}, calibration transform ∈ {none, temperature, vector-scaling}).
  Network weights are *not* the genome at gen 0 — the genome is the configuration space
  around open clones; full-weight evolution is out of scope until H1 survives.
- **Loop:** train on weeks 1–4 (after §10 snapshot exists) → validate on week 5 → select
  top-6 by joint skill → breed (crossover config, mutate LoRA rank / calib transform) →
  retrain → score on week 6 (one-shot, scored once, ever).
- **Generations:** 3 max for the pre-registration test window. Each generation ≈ 12 short
  LoRA runs on INFER2.
- **Seeds recorded.** All RNG seeds committed per generation.

## 8. Hardware plan (per `hermes-stack-verification` homelab layout)

- **INFER2 (RTX 3060 12 GB) — the petri dish.** All LoRA training and inference of
  0.8B-class models. 12 GB is comfortable for 0.8B bf16 LoRA. Currently hosts gitea, n8n,
  open-webui, hoarder, searxng, qdrant — training jobs must be nice (low priority, gated on
  VRAM headroom check before each run).
- **INFER1 (128 GB RAM, hefty AMD CPU) — spare cycles.** Laya-class encoder evals and the
  scorer/prober daemons. Caution: INFER1 hosts the Hermes container itself — nothing in this
  experiment may allocate GPU there (3090 is llama-swap's) and CPU jobs are `nice`d +
  memory-capped containers.
- **INFER3/4: untouched.** No Mac Studio cycles in this experiment.
- **Hard rule: no heavy compute before Maya's sign-off.** Sign-off gates generation 0; the
  telemetry snapshot (§10) is passive collection and is the only thing that runs beforehand.

## 9. What "success" looks like in writing

A table: per question, per generation — model joint log-score, base-rate floor, periodicity
floor, skill, calibration slope, sharpness — plus one paragraph per hypothesis: survived or
falsified, with the numbers that decided it. The interesting failure modes are as valuable as
success: if the population can't beat climatology, the lab's telemetry manifold is either too
noisy at these Δs or the question set is wrong, and the amendment log tells us which.

## 10. Telemetry snapshot plan (runs *before* gen 0; passive, no model compute)

**Finding from today's inventory (2026-10-03):** the lab has no Prometheus/Grafana-monitoring
stack — there is Komodo (container state), dozzle (logs, agents on infer1/infer2 + server on
rxv1), a lone `grafana_owui_infer2` (app-specific, not infra), and Gotify (alerts). So the
nervous system's first organ is a **telemetry sink** that existed nowhere before this project.

Stages (each independently shippable):

1. **Backfill harvest (week 0, read-only).** Komodo API (`ListDockerContainers` per server,
   5-min cadence → JSONL), dozzle log export per service (hourly), existing llama-swap/
   hermes logs parsed retroactively as far back as they go. This gives history to train on
   *before* any new prober exists.
2. **Probers (week 1, lightweight containers on infer1).** 1-min healthcheck matrix +
   5-min Komodo-latency probe + hourly `df` + docker-events tailer → same JSONL sink.
   Low volume by design (~10 MB/day).
3. **GPU samplers (week 1).** `nvidia-smi --query-gpu` at 10-s cadence on infer1/infer2 →
   ring buffer, hourly rollups (mean/max/p95).
4. **Sink & retention.** Append-only JSONL on the persistent `/opt/data` volume
   (`/opt/data/jev-lab/telemetry/YYYY-MM-DD/*.jsonl`), daily gzip, 90-day retention,
   weekly rsync into the existing backup pattern. Schema versioned in the first line of
   every file.
5. **Feature builder (week 2).** Deterministic snapshot → `state` JSON per question family;
   this is the code that defines the "manifold inputs" and gets frozen at registration.

Collection starts only after Maya's veto window (see below) — even passive daemons on infer1
are new surface area and get the same sign-off courtesy.

## 11. Governance & resource accounting

- Registered under the peira-customization project; per the 2026-09-30 governance convention,
  if gen 0+ runs autonomously on a schedule, it gets its own supervised-agent profile entry in
  `ai-constitution/registry/agents.json` with explicit scope (INFER2 LoRA jobs + telemetry
  reads only; no writes to other stacks, no external network beyond HF model pulls).
- Compute budget request (pending): ~12 × 1-h LoRA runs per generation on INFER2, 3
  generations ≈ 36 GPU-hours over ~2 weeks, plus ~5% CPU on INFER1 for probers/scorers.
- Everything reproducible: configs, seeds, data hashes, and this document's commit hash in
  every results table.

## 12. Amendment log

*None yet. Amendments append here with date + rationale; original claims stay visible.*
