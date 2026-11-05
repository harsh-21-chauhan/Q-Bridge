# Research assistant: how it works

The assistant is implemented in **mock mode by default**. A real Muse Spark function call and completed explanation were verified on 5 November 2026. An API key is unnecessary for the prototype walkthrough.

## Reliable startup

Use one command from the repository root in the activated `qbridge` environment:

```zsh
python -m backend.run --live
```

Stop the old backend with Ctrl+C first. If no key exists in that terminal's environment, the launcher prompts privately. Paste it at the hidden prompt, not into a command or chat. The launcher sets live mode and permission together, clears the local pause, and retains every budget reservation. No model request is sent at startup. Keep that terminal open. It never writes the key to disk. A fresh terminal may need the key again.

For mock operation, use `python -m backend.run` without `--live`. This deliberately disables live permission even if old shell exports say otherwise. The launcher refuses an occupied port rather than starting a second backend. Running bare Uvicorn from a fresh terminal does not inherit another terminal's exported key or live settings.

A diagnostic on 5 November found the running server in mock mode, unauthorized, missing its key and paused, with only $0.25 reserved of $5. That combination—not the spending ceiling—blocked live startup. Successful startup does not itself verify the key or billing; the subsequent bounded user-authorized verification succeeded (details below).

## Try it

Start the backend and React using [SETUP.md](SETUP.md). Run or open an experiment, then click **Research assistant**. The main form is for Muse Spark and stays disabled until live mode, authorization and credentials are configured. At the bottom, expand **Model unavailable? Read a local explanation** and click **Explain placement locally** for a read-only Python summary. It works even when model requests are paused and never calls Meta. In live mode, the main form can also request an explicitly selected budget comparison.

The page keeps one question/answer at a time. It sends no chat history. Switching pages clears the displayed conversation; scientific runs remain saved. New comparison runs appear in history after Refresh.

Answers are requested in three short sections: Decision, Evidence and Uncertainty. React renders headings and bullets as safe text, and replaces long internal IDs with readable experiment labels. Exact IDs remain available in saved experiments and expandable technical records. This changes presentation only, not scientific calculations or the model request flow.

## One question, step by step

1. React sends the selected experiment ID, a question and an optional comparison budget to `POST /api/assistant/ask`.
2. FastAPI validates the request. The backend checks the emergency switch and acquires one request lock, shared across local processes.
3. In mock mode, Python selects a tool deterministically. **No HTTP client is constructed.**
4. In future authorized live mode, Muse Spark selects a function tool. Python validates the name and arguments. Tools are scoped to the selected experiment and budget; the model cannot choose arbitrary files, URLs or experiments.
5. Python returns compact evidence. The live adapter sends that evidence back for one final explanation, then stops. Maximum: two provider calls, two distinct tools, one comparison calculation.
6. React displays the explanation and expandable tool evidence. Model prose is not guaranteed correct; the recorded Python results are authoritative.

`get_experiment_evidence` retrieves loss, decision, placements, posterior intervals and calibration stages/EVSI. `compare_budget` uses the existing experiment service with the same saved seed/scenario. Its response excludes simulation truth, actual losses, oracle and regret. Hidden configuration stays inside Python. Expected losses from different posteriors must not be interpreted as direct improvement.

## Spending controls

| Control | Behavior |
|---|---|
| Default mode | `QBRIDGE_ASSISTANT_MODE=mock`; invalid modes fail closed. |
| Authorization | Live requests also require `QBRIDGE_LIVE_AUTHORIZED=yes` and backend `MODEL_API_KEY`. These remain unset/disabled during this stage. No browser control enables live mode. |
| Emergency stop | The pause icon calls `/api/assistant/disable`, persistently disabling subsequent model requests. It becomes a resume icon calling `/api/assistant/resume`. `QBRIDGE_ASSISTANT_DISABLED=true` also blocks requests. An already-sent request cannot be recalled. |
| Persistent budget | SQLite reserves $0.25 before each provider call, with a $5 cumulative allowance. This means at most 20 calls under these defaults. It is deliberately more conservative than estimated token cost. |
| Failure accounting | Timeout, provider errors and crashes retain reservations. There are no automatic refunds, retries or budget resets. |
| Rate/concurrency | Four provider calls per rolling minute; one assistant workflow at a time. |
| Input/output | Questions at most 1,500 characters; complete serialized provider payload at most 24,000 UTF-8 bytes; 1,000 tool-selection tokens and 4,096 final-answer tokens, each including reasoning. The byte bound is a conservative input-size proxy, not an exact token count. |
| Scope | Fixed Muse Spark 1.3 model and official endpoint; no web/image/audio tools, redirects or environment proxies. |
| Usage | Provider-reported tokens are stored when available. Estimated reported cost uses $1.25/M input and $4.25/M output, without a cache discount. Missing usage is not assumed free; the reservation remains. |

The ledger lives in `results/assistant/assistant.sqlite` by default (alongside the configured experiments directory). **Do not delete it to clear an error**: doing so loses budget history. Budget reservations are not actual charges, the Meta credit balance, or a provider hard cap. Other apps/keys, price changes and billing differences are outside these controls. There is no guarantee against card charges.

The emergency switch persists across restarts. Click the play icon to resume. Resume clears only the persistent pause: it does not change mode, authorize live calls, bypass the server disable switch or reset usage. Resume is blocked while a request is still finishing, so it cannot revive a stopped workflow. The read-only local explanation remains available during a pause.

The process lock uses `fcntl` (macOS/Linux). This remains a local, unauthenticated demo: bind to 127.0.0.1; do not expose the backend publicly.

## Code map

- `backend/app/routes/assistant.py`: status, ask, pause/resume and read-only local explanation endpoints.
- `backend/app/services/assistant_service.py`: typed request, evidence tools, mock path, bounded live tool loop, ledger and emergency checks.
- `frontend/src/components/ResearchAssistant.jsx`: selected experiment, question/budget controls, answer and tool trace.
- `tests/test_assistant.py`: mock/network isolation, authorization, persistent budget/stop and fake-provider protocol tests. No genuine credentials are used.

## Official specifications checked on 4 November 2026

The implementation uses [Meta's function-tool protocol](https://dev.meta.ai/docs/cookbook/tool-function-calling), [Chat Completions schema](https://dev.meta.ai/docs/api-reference/chat-completions/schemas) and [pricing](https://dev.meta.ai/docs/pricing-rate-limits). It preserves assistant tool-call IDs and returns matching tool messages. `max_completion_tokens` bounds visible and reasoning output. Raw provider errors and credentials are never returned to the browser or intentionally logged.

Before any real call, obtain the user's explicit testing authorization, recheck pricing and account credit eligibility, set backend-only live settings deliberately, and run one controlled test. Adding a card or creating a key is not that authorization. Successful fake-provider tests do not establish live Meta compatibility.

## Prepare your key safely (5 November 2026)

Mock mode needs only the two existing servers. To prepare live access, sign into the correct team at https://dev.meta.ai/, check that the restriction is gone and promotional credits remain active, then choose **API keys → Create API key**. Name it `qbridge-local`. Do not paste it into chat, screenshots, React, source code or shell command history.

In your **backend terminal**, stop Uvicorn with Ctrl+C. On your Mac's zsh, use the hidden prompt below; paste the key only when prompted:

```zsh
conda activate qbridge
read -rs 'MODEL_API_KEY?Paste Meta API key (hidden): '
export MODEL_API_KEY
export QBRIDGE_ASSISTANT_MODE=mock
export QBRIDGE_LIVE_AUTHORIZED=no
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

This keeps real calls blocked while displaying “Backend key: configured”. The key lasts for this terminal session; the Python server inherits it. `.env.example` is documentation, not an automatically loaded settings file. No key, Team ID, card details or billing credentials belong in frontend configuration.

When live testing is explicitly authorized, stop the backend and set `QBRIDGE_ASSISTANT_MODE=live` and `QBRIDGE_LIVE_AUTHORIZED=yes` in that same terminal before restarting it. The emergency switch must also be off. These settings enable real requests when you press Ask; they do not send a request merely by starting the server. Start with one existing 6-qubit experiment and one explanation request (at most two provider calls, $0.50 reserved application allowance), then check Meta Usage/Billing before doing more. That allowance is not a promised charge or provider cap. Restore mode `mock` and permission `no`, then restart to disable further live use.

On Meta Billing, retain **Free credits in use**, set a low alert under **Spend limits → Set up** (for example $5 or its displayed currency equivalent if accepted), and verify notification delivery. Do not confuse the payment threshold with a cap. If an auto top-up control exists, disable it; this does not disable all pay-as-you-go billing. Check remaining credits and pending usage before/after each test. The app's estimate does not query your Meta credit balance or cover other tools using your team. Do not subscribe to Muse Code to run this API integration.

Official references: [create API key](https://dev.meta.ai/help/api-keys/create-api-key), [spend alerts, not hard caps](https://dev.meta.ai/help/billing/spend-limit-alert). A card-verification hold is separate from promotional API usage. Keeping international payments disabled is not an API budget control.

The assistant now presents authoritative backend evidence as cards and expandable tables; raw JSON remains under Technical tool record. Model prose is displayed separately and cannot supply or overwrite those metrics. Readiness indicators never reveal the credential. Failed questions refresh the ledger display without automatically retrying the model request.


## Submission interface (5 November 2026)

Muse Spark is the main form and answer area, with suggested research questions and a clearly identified source experiment. Answers lead with the model's explanation, followed by authoritative Python evidence cards and tables. Connection, reported token use and the $5 cost allowance are collapsed under **Connection & usage**. These limits still run on every backend request. The small pause/play control has accessible labels and tooltips.

The fallback is a separate, collapsed section at the end. It reads a saved experiment without generating a new experiment or contacting Meta. A provider error does not silently substitute local text for a model answer or retry a chargeable request. No mock result can appear under “Muse Spark’s analysis”. The live badge says “Live enabled”, not “Verified”, because a configured key does not establish provider availability.

## Live protocol correction

The first controlled live request on 5 November returned HTTP 400 for `tool_choice`. Meta's current schema supports only `auto`; OpenAI-style `required` and `none` are not accepted. The adapter now supplies tools with `auto` for the first turn and omits both tools and tool choice for the final explanation. The backend still rejects an answer that has not requested valid evidence. A fake-provider regression test checks this exact payload. The rejected request's reservation was retained; a subsequent real answer succeeded as recorded below.


The corrected live request successfully performed a scientific function call, but its final completion consumed the original 1,000-token cap and did not finish. The final-turn limit was raised to 4,096, with a short-answer instruction; tool selection remains capped at 1,000. No retry is automatic, and incomplete answers are never labeled complete. The $0.25 per-call allowance and $5 cumulative allowance remain unchanged.


## Successful live verification — 5 November 2026

The final authorized test returned HTTP 200 with `mode=live`, a genuine `get_experiment_evidence` function call, and a completed Muse Spark explanation. It used the saved layered 6-qubit, 100-shot experiment `qb_4d088139b797f4dac12a9f10bf903233`. The answer correctly identified placement index 4 as retained, zero expected improvement, no estimated switch probability, and local A as the selected group for both adaptive batches. Model uncertainty statements remain interpretations to check against the numerical evidence, not hardware guarantees.

This successful two-call test reported 1,843 input and 2,445 completion tokens across both calls (including reasoning), an uncached-price estimate of $0.012695. The ledger afterward held $1.50 reserved out of $5, six total provider attempts including earlier failures, and $0.02031125 of estimated reported usage. These are a historical test snapshot, not a current Meta bill or confirmation of a card charge; failed attempts with missing usage are not included in that usage estimate. No further live calls were made for documentation or frontend rendering checks.

The real returned evidence also passed a React server-rendering check. This verifies compatibility with the evidence cards/tables, not browser visual layout. The live what-if comparison and broader prompts still require separate verification. The server remains live-enabled for deliberate user submissions; an idle dashboard only polls local status and makes no model calls.
