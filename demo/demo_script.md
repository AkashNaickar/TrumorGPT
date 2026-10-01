# Demo script - TrumorGPT live run

All outputs below were captured from an actual local run (see `results/` for the full
evaluation). The demo works offline: with `TRUMORGPT_OFFLINE=1` the knowledge-graph builder
uses the deterministic rule-based extractor, so no network or API key is required.

## Start the server

```powershell
$env:TRUMORGPT_OFFLINE = "1"
.venv\Scripts\python.exe -m uvicorn trumorgpt.app:app --app-dir src --host 127.0.0.1 --port 8077
```

## Health and pages

```powershell
curl http://127.0.0.1:8077/health
# {"status":"healthy","pipeline_initialized":true,"knowledge_graphs_indexed":8}

curl -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8077/      # 200 (web UI)
curl -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8077/app   # 200 (app workspace)
```

## Fact-check examples

POST `http://127.0.0.1:8077/api/v1/fact-check` with `{"query": "<claim>"}`.

| # | Claim | Expected verdict | Similarity |
|---|-------|------------------|-----------|
| 1 | mRNA vaccines developed by Pfizer reduce severe COVID-19 hospitalizations. | **True** | 1.00 |
| 2 | Ivermectin is an FDA-approved cure for treating COVID-19. | **False** | 0.50 |
| 3 | A balanced diet helps manage blood glucose in type 2 diabetes. | **True** | 1.00 |
| 4 | COVID-19 causes cancer. | **False** | 0.00 |
| 5 | The 2024 budget deficit widened amid rising interest rates. | **Undetermined** | 0.00 |

### 1 - True (matches a verified KB)
> The statement is true. Semantic health knowledge graph analysis confirms that the claim
> aligns with verified guidelines in 'mRNA Vaccine Efficacy'.

### 2 - False (relational contradiction)
> The statement is false. ... Query claim 'ivermectin claimed_treatment_for covid-19'
> contradicts verified medical evidence 'ivermectin failed_clinical_trials_for covid-19'.

### 3 - True
> The statement is true. ... aligns with verified guidelines in 'Dietary Management of Diabetes'.

### 4 - False
> The statement is false. ... 'covid-19 causes cancer' contradicts verified medical evidence
> 'sars-cov-2 does_not_cause cancer'.

### 5 - Undetermined (out of KB coverage; abstains instead of guessing)
> The claim is undetermined. There is insufficient factual graph overlap in the current
> knowledge base to make a definitive decision.

## curl form

```powershell
$body = @{ query = "Ivermectin is an FDA-approved cure for treating COVID-19." } | ConvertTo-Json
Invoke-RestMethod -Uri http://127.0.0.1:8077/api/v1/fact-check -Method Post `
  -ContentType "application/json" -Body $body
```

## Fact-checking arbitrary claims (optional)

To let the system attempt claims outside the knowledge base, start a local LLM and run the
server **without** `TRUMORGPT_OFFLINE`:

```powershell
ollama serve
ollama pull llama3.1:8b
Remove-Item Env:\TRUMORGPT_OFFLINE -ErrorAction SilentlyContinue
.venv\Scripts\python.exe -m uvicorn trumorgpt.app:app --app-dir src --port 8077
```

Now an out-of-KB claim is answered by the LLM judge (`metrics.verdict_source` shows
`LLM judge (Ollama)`). If no backend is reachable, it stays `Undetermined`.

## Fallback plan if the live demo fails

- If the server will not start: show the captured table above and `results/liar_health_predictions.csv`.
- If the UI is slow: use the curl examples.
- Never rely on the network during the demo; keep `TRUMORGPT_OFFLINE=1`.
