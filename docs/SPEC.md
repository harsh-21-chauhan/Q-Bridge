# Scientific specification — Q-Bridge M1

## Core decision

Given a circuit, labelled QPU capacities, uncertain error parameters and a fixed measurement-shot budget, select **one** diagnostic calibration experiment that minimizes the *expected loss of the best placement decision made after observing it*.

## Circuit families

`ghz`: H on q0, nearest-neighbor CX chain.
`layered`: GHZ preparation followed by deterministic long-range CXs.
`star`: H on q0, star CXs followed by a few extra interactions.

These are **Clifford circuit testbeds**, not generic algorithms or full DQC hardware simulations. Their ideal stabilizer generators follow by conjugating input Z stabilizers through the logical gates.

## Effective noise channel

On each CX `(c,t)` with group parameter `p`:

- I with probability `1-p`
- X on target with probability `p/2`
- Z on control with probability `p/2`

Parameters are `p_A`, `p_B`, `p_remote`. The latter is **effective remote gate error**, not automatically `1 - Bell fidelity`.

For output stabilizer observable S, an error anticommutes if and only if it flips S's expected parity. A CX's error attenuates the expected stabilizer value by `1 - p*m`, where `m` is the number (0,1,2) of the two Pauli errors that anticommute with S at that gate. Conjugating S backwards through all Clifford gates gives the exact attenuation. The task loss is the average incorrect-parity probability across the independent generators:

`L(placement, theta) = mean_S (1 - product_g(1 - p_group(g)*m_(g,S)))/2`.

This diagnostic loss is *not* quantum state fidelity; it is a specified set of observable estimates.

## Calibration and Bayesian model

Each candidate calibration provides idealized independent binary outcomes whose failure probability is exactly its chosen `p`. The model could be implemented by Bell-basis preparation and inverse uncompute on a test CX, treating preparation and measurement as perfect. This is a **simplifying assumption**.

The prior for each `p` is independent Beta(alpha,beta). After `k` failures in `N` shots, posterior Beta(alpha+k,beta+N-k). M1 uses illustrative priors Beta(2,98), Beta(3,97), Beta(4,76), which must not be presented as hardware estimates.

A calibration e is selected by expected value of sample information:

`EVSI(e) = min_a E[L(a,theta)] - E_(k|e)[ min_a E[L(a,theta)|k,e] ]`

The predictive distribution of k is Beta-Binomial. Posterior expected loss is integrated by Gauss-Jacobi quadrature; for the polynomial effective noise model, this is exact up to floating-point accuracy when quadrature order covers the degree.

## Evaluation

Each simulated world samples/defines hidden true parameters. Each policy gets the same shot count. Compare EVSI calibration to random, fixed A, highest-prior-variance, and no calibration. The **same placement optimizer** is used for all policies. Decision regret is `L(chosen,true) - min_placement L(placement,true)` for the small exhaustive experiment. Report mean regret and mean actual task loss; no improvement is assumed.

## Limits and next steps

- Per-gate iid Markovian noise; no coherent, correlated or drifting errors.
- Exact placement enumeration grows combinatorially; use candidate generation/graph-partitioning heuristics beyond the tiny benchmark.
- Generalized Bayesian likelihoods and non-Clifford circuits need alternative inference/evaluation methods.
- Later include conditional Bell fidelity and entanglement success *separately*, waiting-time decoherence and readout effects, with scientifically justified observation models.
- Muse Spark is an orchestrator and explainer for validated numerical tools; no API-based mathematical calculations are trusted without tool provenance.
- All claims about scalability must be supported by actual runtime and quality measurements.
