# Multimodal Construction Intelligence Platform
**Skill Wallet Capstone — Project 1**

A modular Streamlit app for visual site-safety triage, crack-defect triage, early-stage project estimates, and weather-aware construction guidance. It runs without a database and includes demonstration outputs when no Gemini API key is supplied.

## Features
- **Site Safety & PPE Audit:** upload JPG/PNG images; optional Gemini image analysis; PPE checklist, hazard severity/remedies, JSON export.
- **Crack Diagnostics:** defect classification, possible causes, repair/next-step guidance, urgency and JSON export.
- **Planning & Valuation:** editable area, structure, location tier, construction rate and completion; indicative budget, incurred capex, asset-value heuristic, cement and steel quantities; Pollinations AI conceptual-render link.
- **Daily Site Assistant:** weather-condition advisories and optional multi-turn Gemini chat.
- **Demo mode:** app remains usable without an API key.

## Run locally
Python 3.10+ recommended.

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

Open the local URL printed by Streamlit. Add a Google Gemini API key in the sidebar to enable AI features. The key is entered at runtime and is not saved by the app.

## Deploy to Streamlit Community Cloud
1. Create a new GitHub repository.
2. Upload `app.py`, `requirements.txt`, `README.md`, `.gitignore`, and `.streamlit/config.toml`.
3. In Streamlit Community Cloud, create an app from that repository and select `app.py` as the main file.
4. Deploy. No secrets are required for demo mode.
5. To use Gemini, enter the API key in the app sidebar. **Never commit API keys to GitHub.**

## Important safety and valuation limitations
- This is an educational decision-support capstone, not a professional inspection or certification system.
- A single image cannot reliably establish PPE compliance, hidden footwear, crack width, crack activity, or structural integrity.
- IS 456 relates to plain and reinforced concrete; it is not a PPE standard. Follow applicable Indian safety rules, project requirements, and relevant OSHA guidance where applicable.
- Structural cracks, exposed reinforcement, displacement, widening cracks, or suspected instability require a qualified structural engineer. Do not use the app to decide that a building is safe.
- Cost, asset valuation and material coefficients are illustrative placeholders. Replace them with current local rates, drawings, BOQ, site-specific design and quantity-surveyor input.
- Pollinations AI is a third-party service. Its availability, generated content, and terms are outside this app's control.
- Images and chat are sent to Google only when Gemini is enabled and an AI feature is invoked. Review the provider's privacy terms before using sensitive project images.

## Project structure
```text
multimodal_construction_intelligence_platform/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
└── .streamlit/
    └── config.toml
```

## Troubleshooting
- If Gemini is unavailable, check the key, API access, network connection and current model availability. The app falls back to demo output.
- If deployment fails, check the Streamlit build logs and ensure `requirements.txt` is committed.
- For a production deployment, add authentication, request quotas, audit logging, and an approved data-retention policy before handling confidential project data.
