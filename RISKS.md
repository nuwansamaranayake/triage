# Risk Register: Triage

A living register. Each risk has an owner, a concrete tripwire (an observable signal that says the
risk is materializing), and a status. Seeded from the chapter's Failure Modes and Mitigations;
updated as the system is built and evaluated.

| Risk | Owner | Tripwire | Status |
|---|---|---|---|
| **Cluster instability makes issues flicker.** Unstable clustering causes the same underlying complaint to split, merge, or oscillate its lifecycle state, producing phantom issues and destroying trust in the registry. Mitigation: seeded clustering, minimum-support thresholds, hysteresis on state transitions. | eng lead | An issue's cluster membership changes across two consecutive nightly runs, **or** any issue toggles between two lifecycle states (e.g. `emerging <-> growing`) more than twice within a 48-hour window. | open |
| **Hypotheses read as proof.** A guarded causal hypothesis is presented downstream as established cause, letting a `plausible_hypothesis` drive engineering decisions it has not earned. Mitigation: guarded states rendered in every surface, alternative candidate events listed, promotion requires deterministic evidence checks. | eng lead | Any exported ticket, digest, or API response references a causal event without its accompanying guarded-state token, **or** a hypothesis still in `plausible_hypothesis` / `inconclusive` is cited as the cause in outbound narration. | open |
