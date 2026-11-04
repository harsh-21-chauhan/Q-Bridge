# Research assistant: how it works

The assistant is implemented in **mock mode by default**. No live Meta request has been made or verified. An API key is unnecessary for the prototype walkthrough.

## Try it

Start the backend and React using [SETUP.md](SETUP.md). Run or open an experiment, then click **Research assistant**. Ask for a mock walkthrough. Expand the tool evidence to see the numbers behind it. Optionally choose a budget to run a real local Python comparison. Mock answers are fixed evidence summaries, not natural-language understanding or Muse Spark output.

The page keeps one question/answer at a time. It sends no chat history. Switching pages clears the displayed conversation; scientific runs remain saved. New comparison runs appear in history after Refresh.

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
| Emergency stop | The button calls `/api/assistant/disable`, persistently disabling subsequent requests. `QBRIDGE_ASSISTANT_DISABLED=true` also blocks requests. An already-sent request cannot be recalled. |
| Persistent budget | SQLite reserves $0.25 before each provider call, with a $5 cumulative allowance. This means at most 20 calls under these defaults. It is deliberately more conservative than estimated token cost. |
| Failure accounting | Timeout, provider errors and crashes retain reservations. There are no automatic refunds, retries or budget resets. |
| Rate/concurrency | Four provider calls per rolling minute; one assistant workflow at a time. |
| Input/output | Questions at most 1,500 characters; complete serialized provider payload at most 24,000 UTF-8 bytes; 1,000 completion tokens including reasoning. The byte bound is a conservative input-size proxy, not an exact token count. |
| Scope | Fixed Muse Spark 1.3 model and official endpoint; no web/image/audio tools, redirects or environment proxies. |
| Usage | Provider-reported tokens are stored when available. Estimated reported cost uses $1.25/M input and $4.25/M output, without a cache discount. Missing usage is not assumed free; the reservation remains. |

The ledger lives in `results/assistant/assistant.sqlite` by default (alongside the configured experiments directory). **Do not delete it to clear an error**: doing so loses budget history. Budget reservations are not actual charges, the Meta credit balance, or a provider hard cap. Other apps/keys, price changes and billing differences are outside these controls. There is no guarantee against card charges.

The emergency switch persists across restarts. To restore mock operation after testing it, stop the backend, keep mode set to mock, and have the local operator set `controls.disabled` back to `0` in this SQLite database. Do not remove the `calls` table or database. No HTTP re-enable endpoint exists.

The process lock uses `fcntl` (macOS/Linux). This remains a local, unauthenticated demo: bind to 127.0.0.1; do not expose the backend publicly.

## Code map

- `backend/app/routes/assistant.py`: three small endpoints: status, ask and disable.
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
