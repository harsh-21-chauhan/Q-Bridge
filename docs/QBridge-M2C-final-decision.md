# Q-Bridge — M2C algorithm decision (4 Nov 2026)

## Scope and provenance
Analyzed the submitted `QBridge-M2C-full-runs100.zip` and `QBridge-M2C-quick-runs30.zip`, with comparisons informed by the M2C validation implementation. The 100-run archive covers 40 configurations: GHZ, layered, and star circuits; 6 and 12 qubits; 50/100/200-shot budgets; prior and shifted truth models; plus local-only and link-only shifts for layered 12q at 100/200 shots. There are 100 trials per configuration and 8 policies per trial (32,000 policy outcomes). Importantly, seeded ground-truth vectors are shared across several configurations (991 unique noise triples in 4,000 trial/configuration observations), and the quick 30-run data are exactly a prefix of corresponding full-run cases; they are not an independent replication. All observations are simulated, not physical quantum measurements.

## Aggregate results
Equal-weighted means across 40 configurations. Regret values here are multiplied by 1,000. Smaller is better. Harm is the percentage of trials where calibration caused a worse placement than the uncalibrated incumbent.

| Policy | Mean regret x1,000 | Harm rate | Help rate | Switch rate |
|---|---:|---:|---:|---:|
| Adaptive EVSI + original priors + 60% switch guard | **1.299** | **4.45%** | 7.60% | 12.05% |
| Adaptive EVSI + mixture priors + 75% switch guard | 1.311 | 1.62% | 4.15% | 5.78% |
| Adaptive EVSI + original priors, no guard | 1.318 | 7.43% | 10.65% | 19.00% |
| Adaptive EVSI + original priors + 75% switch guard | 1.351 | 1.10% | 3.10% | 4.20% |
| Fixed split | 1.447 | 6.70% | 7.60% | 16.10% |
| No calibration (uses zero shots) | 1.484 | 0.00% | 0.00% | 0.00% |
| Original one-step EVSI | 1.530 | 11.55% | 10.00% | 21.55% |
| Random calibration | 1.617 | 7.28% | 5.90% | 14.38% |

## Important statistical caveat
Compared with the unguarded adaptive method, the mean advantage of the 60% guard is only 0.0193 x1,000 regret units (approx. 1.5% relative reduction). A bootstrap clustered by trial index across configurations gives a 95% interval for the improvement of **[-0.0706, +0.1084] x1,000**, which includes zero. Therefore the benchmark does **not** establish that a 60% guard is generally more accurate than unguarded adaptive EVSI. Versus original one-step EVSI the same calculation shows a larger mean improvement of +0.2312 x1,000 (95% interval approximately [+0.1069,+0.3540] x1,000), although repeated simulated environments and many comparisons warrant care.

## Heterogeneity (mean regret x1,000)

| Condition | Original one-step EVSI | Adaptive, no guard | Adaptive + 60% guard | Adaptive + 75% guard (original priors) | No calibration |
|---|---:|---:|---:|---:|---:|
| Prior-aligned | 1.570 | **1.578** | 1.660 | 1.762 | 1.924 |
| Both noise types shifted | 1.142 | 0.807 | 0.644 | 0.560 | **0.538** |
| Link-only shifted (layered 12q) | 2.602 | 1.174 | **1.150** | 1.399 | 1.820 |
| Local-only shifted (layered 12q) | **3.604** | 3.725 | 4.102 | 4.715 | 5.698 |

The blanket guard protects against harmful switches under both-shifted conditions, but can block beneficial switches when local errors alone shift. In some GHZ shifted settings the no-calibration incumbent is already optimal nearly always; calibration cannot improve it and can introduce regret. A threshold is a tunable risk preference, not a guaranteed accuracy improvement.

## Decision for the hackathon MVP
**Freeze the scientific core as sequential adaptive Bayesian EVSI with the original Beta priors** (pilot sampling A/B/link; posterior update; two adaptive EVSI batches). Make an **optional 60% posterior-improvement guard** the default *conservative product mode* because it noticeably reduces harmful switches, while leaving unguarded adaptive EVSI accessible for users who prioritize expected task loss. Retain original one-step EVSI, random/fixed calibration and no calibration as baselines. Keep the mixture-prior/75%-guard variant under an experimental toggle or in the benchmark, not as the default scientific claim.

For a 100-shot example: 10 shots on local A, 10 on local B, 20 on the link, then 30+30 chosen sequentially by EVSI. The guard compares the new candidate with the incumbent under posterior samples and accepts only if estimated P(new loss < incumbent loss) >= 0.60 and posterior expected gain is positive. This policy can still be confidently wrong when its likelihood or prior is misspecified.

## Limitations to disclose
- Binary diagnostic measurements and three grouped effective noise rates, not full quantum-device calibration.
- Small structured Clifford circuit families; 6q exhaustive and 12q exhaustive placement, not large-scale quantum hardware scaling.
- Output-parity task loss, not universal process fidelity.
- Simplified remote-operation channel, not physically implemented distributed gate teleportation.
- Shared simulator assumptions between decision model and evaluation oracle; no device or held-out hardware validation.
- No calibration and calibration policies use different shot counts by design (0 vs budget), so compare task-loss benefit and shot cost separately.
- The 30-run zip is subsumed by the 100-run zip; no additional independent replication.
- Scenario-level intervals are uncorrected for multiple comparison and the overall optimum is sensitive to scenario weighting.

## Immediate next development priorities
1. Freeze algorithm and APIs; add standardized, reproducible experiment IDs and provenance.
2. Build a FastAPI endpoint that returns circuit, allocation trace, posterior means, prior and recommended placement, risk information and baseline comparison.
3. Build a simple dashboard that visually communicates one 100-shot experiment and lets a user vary circuit family/budget.
4. Integrate an actual eligible Meta model using tool calls to backend functions, and distinguish model explanation from computed scientific evidence.
5. Record the 3-minute demo and clearly label simulations and known scientific limitations. Do not delay the submission for another algorithm-tuning cycle.
