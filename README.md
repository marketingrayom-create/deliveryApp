# Delivery Atlas

Run `powershell -ExecutionPolicy Bypass -File .\start.ps1` in this folder, then open http://127.0.0.1:5055.
For an explicitly desired LAN run: `.\.venv\Scripts\python.exe app.py --host 0.0.0.0 --port 5055`. This local prototype has no login; use it on a trusted local machine/network.

1. Select regions and tiers. The app supplies an editable ten-city business shortlist per region (60 total); some regions have fewer or no Tier 1 cities.
2. Select cities using checkboxes. Each city uses one editable fixed representative pincode; results do not represent every pincode in that city.
3. Paste ASINs or import an .xlsx with ASIN/Brand columns (the provided workbook is supported). Enter the source location. Choose a category if product titles are unavailable.
4. Start the check, watch results, and export Excel. Four sheets: City Comparison Matrix, Delivery Details, Recommendations, Run Settings.

Delivery results are real Amazon browser promises. The requested pincode must appear in the location header before a date is accepted. No fallback cookies, CAPTCHA bypass, invented dates, or claims that an unavailable listing is suppressed. Verification errors stay visible and exportable.

General recommendations are product/climate fit rules. Seasonal recommendations use Open-Meteo current model temperature/humidity, with timestamps. Missing weather/category means no guessed conclusion. Air-purifier demand requires AQI and is not inferred from weather. These are suitability suggestions, not validated sales forecasts. The origin field records your analysis source; Amazon dispatch origin cannot be controlled by that field.

City data: `cities.py` defaults, editable in the UI; saved to `data/cities.json`. Tier labels are editable business groupings, not government classifications or a measured top-ten ranking. Suggested pincodes can be verified against https://www.indiapost.gov.in/vas/Pages/LocatePostOffices.aspx.
Weather documentation: https://open-meteo.com/en/docs.

Job history and partial results persist in `data/runs.sqlite3`. A server restart marks running jobs interrupted; saved results remain exportable. Only one run executes at a time, with two isolated city browser workers. Up to 1,000 ASINs / 10,000 combinations per run. Cancellation may wait for the current browser request to finish.

Test: `.\.venv\Scripts\python.exe -m unittest test_app.py`.

Amazon verification: enable Show Amazon browser for a check if the headless session is challenged. Complete verification manually in the browser on the app/server computer; the worker waits up to two minutes. Each city has an isolated persistent browser profile under data/browser-profiles. These profiles can contain session data; they are excluded from Git. No verification is bypassed. The live test was challenged, so a live delivery date was not verified during setup.

Updated selection policy: each selected region has 10 cities in each editable regional business Tier 1/2/3 group (180 cities total). These are not official national Tier-1 classifications and are not verified GDP ranks. Comparable city GDP data was not available; no GDP values were invented. Optional per-city GDP fields require a common year and source before a GDP sort can be used. Source city typing is removed; only the checkbox-selected destinations are checked and exported as Selected City. Ordinary Edge browser is visible by default, with six-second spacing and one city worker. Verification stops the run and retains checked results; retry is a manual user action.

Latest recommendation/export policy: only City Comparison and Recommendations are exported. City-wise sales are explicitly unavailable and sales priority is unranked until actual sales are supplied. Fan/weather priority uses destination temperature (High >=28°C, Medium >=24°C, Low below24°C), not an assumed October sales trend. The browser matches consent-based geolocation to a listed city within50km locally and sends only the city ID; precise GPS coordinates never leave the browser. Public city coordinates are used for weather, and source/destination timestamps are reported. ASIN entry time/month are retained. Parallel city workers:2; normal page spacing:2seconds; verification or429/403/503 still stops checking.

## GroqCloud recommendations
New checks use GroqCloud Chat Completions with strict structured JSON output. Add your own key to `.env`:

```env
GROQ_API_KEY=your_groq_key_here
GROQ_MODEL=openai/gpt-oss-120b
```

Create your key at https://console.groq.com/keys. The model name contains `openai/`, but inference is performed through GroqCloud using the Groq key. No OpenAI API key is required for new checks. This default model supports strict JSON schema on Groq. Other models may not support this output format; confirm support before changing the model.

Restart the app with `.\.venv\Scripts\python.exe app.py --port 5056` and refresh the browser. Existing EXE files require rebuilding to include these source changes. Key changes apply to new checks; keys are read server-side from `.env` or environment variables. Existing provider credentials are retained, but new checks do not silently fall back to OpenAI or Gemini.

The shared prompt in `analysis_prompt.py` uses Amazon's approximate “bought in past month” product-level badge for general recommendations. Seasonal advice analyzes next calendar month from the execution date in India, including December/January year rollover. Product identity, destination city/PIN, badge and recorded weather evidence are sent; source location, precise GPS, cookies and credentials are excluded.

Live AQI and full-month forecasts are not connected. Typical seasonality is labeled uncertain; stock quantities, city sales and profit are not invented. Missing keys, rate limits, access errors, refusals and incomplete/invalid replies retain local rules with visible status. Temporary rate-limit errors are retried with bounded waiting; Groq project limits still apply.

Tests: `.\.venv\Scripts\python.exe -m unittest test_groq test_openai test_gemini test_purchase_badge test_export_matrix`.
Documentation: https://console.groq.com/docs/structured-outputs.

Fresh-run policy: starting a valid new check clears all previous run/results records in one database transaction. Existing browser profiles, city settings and downloaded Excel files are retained. The browser stores the current run only for the current tab session.

## Windows EXE
Double-click `AmazonDeliveryApp_Groq.exe`. It starts the local app on http://127.0.0.1:5056 and opens your default browser. Stop any Python server using port 5056 first. Keep your configured `.env` alongside the EXE. Microsoft Edge must be installed for Amazon checks. Runtime data and logs are stored in the adjacent `data` folder. Rebuild with `.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --distpath . --workpath build\groq AmazonDeliveryApp_Groq.spec`.

Current market shortlist: 203 cities using the supplied regional e-commerce Tier 1–4 lists. Tier 1 counts: North 10, South 4, East 1, West 5, Central 2, North East 1. Tiers 2–4 have 10 cities per region. Pune is West only; Warangal replaces the South placeholder; Rajnandgaon replaces Udaipur in Central. These are user business tiers, not independently verified market ranks. Representative PINs are suggested and should be verified for the exact delivery area.

Fast export: while the browser tab stays open, Excel downloads once 10 seconds after scraping finishes. It does not wait for Groq analysis. Reports exported before AI completion have `_AI_pending` in the filename and visible progress status; download again after completion for final recommendations. Pending reports are never retained in the completed-export cache. Use `AmazonDeliveryApp_Groq_Fast.exe` for this behavior.

Current AI export policy: use `AmazonDeliveryApp_Groq_AI.exe`. Groq read timeout is 180 seconds per batch (connection timeout 15 seconds). Excel auto-download waits until AI processing finishes, then starts after 10 seconds while the browser remains open. Early pending exports are blocked. API quota or access failures remain visible; a longer timeout does not resolve these errors.
