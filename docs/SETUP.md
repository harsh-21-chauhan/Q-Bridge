# Run Q-Bridge locally

The scientific interface, FastAPI backend and React dashboard are implemented. Run Python and React in two separate terminals. No API key or paid service is required; the assistant defaults to mock mode. See [the assistant guide](ASSISTANT_WALKTHROUGH.md).

## 1. Open the repository and activate Python

```bash
cd /Users/harshchauhan/Desktop/Q-Bridge
conda activate qbridge
```

Use your existing `qbridge` Conda environment. The dependency command below uses that environment's Python, including Uvicorn. There is no need to create another environment.

On a new computer, create a fresh environment instead:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows, use `.venv\Scripts\activate`.

## 2. Install dependencies

```bash
python -m pip install -e '.[api,dev,api-test]'
```

The command installs the project in editable mode: changing a Python file changes the code the server uses, without copying it elsewhere. `api` adds FastAPI, Pydantic and Uvicorn; `dev` adds pytest; `api-test` adds HTTPX for tests. NumPy/SciPy remain the scientific dependencies. Optional Aer checks require `python -m pip install -e '.[aer]'`.

The verified backend environment used Python 3.11.18, FastAPI 0.162.0, Pydantic 2.14.2, Uvicorn 0.54.0, HTTPX 0.28.1, NumPy 2.4.6 and SciPy 1.17.1. Dependency ranges are declared in `pyproject.toml`; this is a tested version snapshot, not a cross-platform lockfile.

## 3. Start the server

```bash
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Keep that terminal open. `--reload` restarts the development server after code changes. `127.0.0.1` keeps this unauthenticated MVP on your own computer. Use one worker for the local demo. Press Ctrl+C to stop.

Open:

- [Interactive API page](http://127.0.0.1:8000/docs): try requests and inspect responses.
- [Health check](http://127.0.0.1:8000/api/health): confirms the process is running.
- [Benchmark data](http://127.0.0.1:8000/api/benchmarks/summary): reads the verified precomputed M2C summary.

The interactive documentation UI loads its browser assets from a public CDN, so viewing `/docs` needs internet access for those assets. The experiment and benchmark APIs themselves make no external calls. Command-line requests below work without the documentation UI.

## 4. Start React in a second terminal

Install Node.js 22.12+ (or another version supported by Vite 7), then run:

```bash
cd /Users/harshchauhan/Desktop/Q-Bridge/frontend
npm ci
npm run dev
```

Open [the dashboard](http://127.0.0.1:5173). Keep both terminals open. Click **Run calibration** to create a real local Python simulation. Editing controls alone does not run a calculation. The default is layered, 6 qubits, 100 shots, seed 42 and the 60% guard. A retained placement is a valid outcome.

After the first dependency install, use only `npm run dev` for daily work. Node packages live in `frontend/node_modules`; Python dependencies live in Conda. Neither directory belongs in Git.

Vite forwards browser `/api` requests to port 8000. If your backend already runs there, reuse it. If you deliberately choose another port, for example 8001, start React with:

```bash
QBRIDGE_API_TARGET=http://127.0.0.1:8001 npm run dev
```

Alternatively, copy `frontend/.env.example` to `frontend/.env.local` and change the target, then restart Vite. Unlike the Python configuration, Vite loads this frontend environment file automatically. Do not add API keys or any `VITE_` secrets.

To check the production build locally:

```bash
npm test
npm run build
npm run preview
```

Preview opens on [port 4173](http://127.0.0.1:4173) and still needs FastAPI. This is local preview, not a deployment. See the [dashboard walkthrough](FRONTEND_WALKTHROUGH.md) for screens, code organization and demo guidance.

## 5. Optional: run an experiment directly through the API

On `/docs`, expand **POST /api/experiments**, click **Try it out**, enter this body, and click **Execute**:

```json
{
  "family": "layered",
  "qubits": 6,
  "shots": 100,
  "seed": 42,
  "truth_mode": "shifted",
  "method": "adaptive_evsi",
  "guard_enabled": true,
  "guard_threshold": 0.60,
  "guard_draws": 512
}
```

Or use another terminal:

```bash
curl -sS http://127.0.0.1:8000/api/experiments \
  -H 'Content-Type: application/json' \
  -d '{"family":"layered","qubits":6,"shots":100,"seed":42}'
```

The omitted fields use the same defaults shown above. A new saved experiment returns HTTP **201**. Repeating identical settings returns **200**, the same ID and the existing identical record. Copy `experiment_id` into **GET /api/experiments/{experiment_id}** to retrieve it, or use the response's `Location` address.

The result contains `result.calibration`, `result.final_posterior`, `result.placements`, `result.loss` and `result.decision`. `evaluation` is separate simulator-only grading. See the [walkthrough](BACKEND_WALKTHROUGH.md) for how to explain these fields.

## API reference

| Method and path | Purpose |
|---|---|
| `GET /api/health` | Process status; does not promise that disk or evidence is available |
| `POST /api/experiments` | Run and save one validated final-method experiment |
| `GET /api/experiments?limit=20&offset=0` | Paginated saved history, in stable ID order |
| `GET /api/experiments/{experiment_id}` | Retrieve the full saved record |
| `GET /api/experiments/{experiment_id}/evidence` | Retrieve only measurement/posterior decision evidence |
| `GET /api/benchmarks/summary` | Eight aggregate policies and all 40 full M2C scenario breakdowns |

The assistant exposes `/api/assistant/status`, `/api/assistant/ask`, `/api/assistant/disable`, `/api/assistant/resume` and `/api/assistant/explain`; see the assistant guide. Only `adaptive_evsi` is accepted for new experiments; the benchmark endpoint contains historical baseline comparisons. Changing `shots` with the same seed/scenario preserves the simulator's underlying environment and measurement prefixes, as documented in the scientific interface. No claim is made that more shots must produce a better individual result.

## Files and configuration

Saved experiments go to `results/experiments/<experiment_id>.json`, which is ignored by Git. Restarting the server preserves them. Files are published only after a complete JSON write; identical requests cannot create duplicate records. The store checks record structure, shot accounting and configuration identity. It is not a cryptographic audit system or a substitute for scientific regression tests.

The backend reads frozen benchmarks from `research/`. It verifies the full summary's checksum, excludes overlapping quick trials and caches the parsed report until restart. Do not edit frozen evidence to change the charts.

Optional environment settings:

```bash
export QBRIDGE_EXPERIMENT_DIR=/absolute/path/to/local/experiments
export QBRIDGE_RESEARCH_DIR=/absolute/path/to/Q-Bridge/research
```

Use separate directories for evidence and generated experiments. `.env.example` documents these names, but `.env` files are **not automatically loaded**. No Meta key is needed in mock mode; only explicitly authorized live mode reads it. A built wheel includes both Python packages, but deliberately does not duplicate research archives; point `QBRIDGE_RESEARCH_DIR` to the checkout when running an installed wheel elsewhere.

## Tests and common errors

```bash
python -m pytest -q
python3 scripts/verify_research_evidence.py
```

The completed backend run passed **176 tests**, including optional Aer checks. With scientific dependencies only, backend test modules are skipped; install the `api` and `api-test` extras for the full suite. The installed Starlette test client currently emits one HTTPX deprecation warning; tests and the live server work. No model calls are used by any test.

| Status / symptom | Meaning and action |
|---|---|
| `422` | Invalid configuration or ID. Check the named field; sizes are 6/12 qubits, budgets 20–1000. Numeric strings and unknown methods are rejected. |
| `404` | No saved experiment for that valid ID. Run an experiment first. |
| `409` | The same ID already has different contents. The server refuses to overwrite it. Inspect the record locally. |
| `500` with saved-record message | The saved record is damaged/inconsistent. The original is left in place for inspection. |
| `503` calculation busy | Another calibration is running in this worker. Wait for it to finish before starting another. No automatic retry is performed. |
| `503` storage unavailable | Check the experiment directory and disk permissions. |
| `503` benchmark unavailable | Check the research directory and run the evidence verifier. |
| `No module named fastapi` | Activate the environment and install `.[api,dev,api-test]`. |
| Port already in use | Stop the other local server or choose another port and use that port in the browser. |

This is a local MVP, not a publicly secured deployment. Browser CORS permissions are not opened globally; Vite uses a development/preview proxy to reach the backend. If port 5173 is occupied, stop your previous frontend with Ctrl+C; strict port selection avoids silently opening a different server.


For the research assistant's live demo, prefer `python -m backend.run --live` from the root instead of a sequence of shell exports. It privately prompts for a missing key, configures live permission, resumes the assistant and preserves usage limits. Stop the previous backend first; keep the frontend running separately. No model call occurs until a question is submitted. See [the assistant guide](ASSISTANT_WALKTHROUGH.md).
