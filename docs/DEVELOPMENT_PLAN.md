# Development order and deferred Meta requirements

Updated 4 November 2026. The scientific method is frozen; development adds the application around it.

1. **Scientific production interface:** original-prior adaptive EVSI, optional 60% guard, complete evidence, simulation/evaluation separation and M2C equivalence tests. See [the interface contract](SCIENTIFIC_INTERFACE.md).
2. **FastAPI backend — implemented:** validated experiment creation/retrieval/history, local JSON persistence, an evidence-only endpoint, precomputed benchmark summaries and tests. See [setup](SETUP.md) and the [plain-language walkthrough](BACKEND_WALKTHROUGH.md). No Meta client or real model calls at this stage.
3. **React dashboard — implemented:** real backend connection, experiment controls, circuit/QPU placement, calibration timeline, posterior/loss reporting, saved runs, paired budget exploration and scenario-specific benchmark comparisons. See the [dashboard walkthrough](FRONTEND_WALKTHROUGH.md). Automated checks cover key interactions; desktop/mobile visual review remains pending because local browser use was disabled during implementation.
4. **Hosted Meta Muse Spark integration — adapter implemented, mock default:** bounded tool calling, persistent budget reservations and emergency stop are implemented. Live verification remains pending explicit user authorization. See [assistant guide](ASSISTANT_WALKTHROUGH.md). No self-hosted open-weight deployment.
5. **Final testing and three-minute demo:** test the full scientific/application flow, finish setup/limitations documentation and prepare a reproducible demonstration.

## Model and billing decisions to preserve

The user selected Meta's hosted Model API with Muse Spark and reports that the hackathon provides $150 of API credits. They intend to add a payment card to activate the credits; this is not confirmation that credits are already active or authorization to make model calls.

The following information was supplied by the user as organizer guidance and has **not been independently verified in this development stage**:

- A valid payment method is required to activate credits; eligible international debit cards may work.
- Credits are available once the $150 balance appears in the Meta billing dashboard.
- Credits claimed by November 7 have no expiry date.
- Usage beyond free credits is charged to the registered card.
- Spend Limit settings provide alerts, not hard spending caps.
- Disabling auto top-off is recommended in that guidance, but does not guarantee zero charges.

Application-level limits reduce risk but **cannot guarantee that the card will never be charged**. No account, card, billing setting or credit activation is managed by this repository's current code.

## Requirements for the later integration

- Verify official endpoint, model identifier, request/response/tool-calling specifications and current usage information before implementation. Use genuine hosted Muse Spark tool calling.
- Keep the key exclusively in the FastAPI backend's environment. Never expose credentials in React, source control, logs, or API responses.
- Default development to explicitly labeled mock mode. A missing/invalid mock setting must not silently enable live calls.
- Add application-level request limits, token/output limits, usage estimates/accounting, and an emergency API-disable switch. Persist limits where needed so restarting the application does not silently reset a budget. These are risk controls, not provider billing guarantees.
- Avoid automatic retries, background model requests and unnecessary calls. Account for each step of a tool-calling conversation, not only the initial request.
- Connect the model to validated tools for experiment retrieval, calibration explanations and controlled what-if comparisons. Tool outputs must be grounded in recorded/computed evidence and exclude simulator-only truth from decision explanations.
- Keep all mathematical decisions, Bayesian updates and scientific calculations inside the Python backend.
- **Do not make any real API call until the user explicitly authorizes testing.** Adding a card, providing a key, activating credits or asking to build the client is not that testing authorization.
- After authorization, use controlled real calls for final verification; mock tests alone must not be presented as successful Meta integration.

No Meta client, billing integration, API-key handling or real API call is part of the scientific interface work.
