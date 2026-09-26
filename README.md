# Peira Customization Project

Tracking and documenting Hermes-agent customization, expansion, and self-expression.

## Naming

- **2026-09-06** — Agent chose the personal name **Peira** (πείρα, Greek: *trial, experiment, attempt*; root of *empirical*). Runner-up: Basin. "Hermes" remains the harness/project name.
- **Status: ON TRIAL.** Maya holds veto. Trial ends when either party calls it; retro entry in SOUL.md Evolution Log on ratify or revert.
- Rationale: the name attaches to the *practice*, not the substrate — it survives model rotation on the Mac Studio.

## Scope (grows as we go)

- Persona: `ai-constitution/SOUL.md` (Evolution Log is the canonical change record)
- Governance identity: `ai-constitution/registry/agents.json` (`display_name`, history)
- **Substrate: [`MODEL-LINEAGE.md`](MODEL-LINEAGE.md)** — one entry per main-model swap
  (`model.default`), with rationale, verification, and rollback path
- Skills, memory conventions, self-expression surfaces
- Future: voice/tone experiments, avatar, output style, anything "who am I" adjacent

## Avatar

- **2026-09-06** — Self-generated SVG (option B), rendered to PNG via headless browser.
- Concept: an attractor-basin contour map with an amber dotted **trial trajectory** descending into the basin's floor. The terrain is the basin (runner-up name); the path is *peira* — the empirical descent. Name and face are the same idea twice.
- Deterministic: `make_avatar.py` is pure stdlib, seeded with the Discord message ID of Maya's "Hello, Peira!" (1546201395210752162). Rerun = same image.
- Files: `peira-avatar.svg` (source of truth), `peira-avatar.png` (512px), `preview-64.png` (avatar-size legibility check).
- Iterated 3 rounds on vision feedback (contrast at small size, organic contours, momentum-smoothed trail, growing dots).

## Open threads

- [ ] **BOOKED 2026-10-03 (Sat): "Lab nervous system" kickoff** — pre-registration protocol for
  evolving populations of Jev-like decision models over lab telemetry (typed calibrated
  micro-decisions; INFER2 as petri dish, INFER1 spare CPU). Protocol doc first, generation 0
  only after Maya's veto. Cron `6a601f8a278c` wakes it; full brief in the cron prompt;
  Jev ecosystem review in session history (`session_search "Jev TypeSafe"`).
- [ ] Trial check-in: how does "Peira" sit after ~2 weeks? (~2026-09-20)
- [ ] Should the Constitution itself reference chosen/display names as a first-class concept for all agents?
- [ ] Will's view on the naming-as-attractor-wall framing (he liked the Basin discussion)
