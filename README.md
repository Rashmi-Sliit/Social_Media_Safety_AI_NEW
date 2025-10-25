# Social Media Safety AI (Streamlit Demo)

This small demo processes a CSV of social media comments through four simple agent modules:

- `content_analyzer.py` — Detects bad language, hate speech, PII, scam patterns; extracts sentiment, emotion, topic; summarizes and optionally creates an embedding.
- `risk_detector.py` — Computes a risk score and level using weighted heuristics.
- `advice_agent.py` — Generates human-readable advice and moderation suggestions.
- `mitigation_agent.py` — Computes toxicity, categorizes, decides mitigation action and returns reasoning.

The Streamlit app `app.py` uploads a CSV, runs each row sequentially through the agents, and shows per-agent tabs with tables and charts. It also provides an "Overview" and a button to show the full backend workflow for the first CSV row.

CSV format

The CSV must include the following columns:

- userID
- username
- comment_id
- comment

Run

1. Create a virtual environment (recommended).

2. Install requirements:

```pwsh
pip install -r requirements.txt
```

3. Run the Streamlit app:

```pwsh
streamlit run app.py
```

Notes

- This demo uses simple rule-based heuristics and random embeddings for offline, local testing. Replace with real ML models or external APIs as needed.
- The agents are implemented as separate Python modules to make it easy to swap in HTTP-based free APIs later.

Using external free APIs (optional)

Each agent can instead call an external HTTP API if you set the appropriate environment variable. The app will attempt a POST and fall back to local logic if the request fails.

- `CONTENT_ANALYZER_URL` — POST to `{CONTENT_ANALYZER_URL}/analyze` with payload {userID, username, comment_id, comment}
- `RISK_DETECTOR_URL` — POST to `{RISK_DETECTOR_URL}/detect` with the content analyzer output
- `ADVICE_AGENT_URL` — POST to `{ADVICE_AGENT_URL}/advise` with the risk detector output
- `MITIGATION_AGENT_URL` — POST to `{MITIGATION_AGENT_URL}/mitigate` with combined outputs

Set environment variables before running Streamlit. Example (PowerShell):

```pwsh
$env:CONTENT_ANALYZER_URL = "https://example.com"
$env:RISK_DETECTOR_URL = "https://example.com"
pip install -r requirements.txt
streamlit run app.py
```
