import json
import os
import re
from datetime import datetime
from urllib.parse import quote

import streamlit as st
from PIL import Image

try:
    from google import genai
    from google.genai import types
except Exception:
    genai = None
    types = None

APP_TITLE = "Multimodal Construction Intelligence Platform"
MODEL_NAME = "gemini-2.5-flash"

st.set_page_config(page_title=APP_TITLE, page_icon="🏗️", layout="wide", initial_sidebar_state="expanded")

# ---------------------------- Styling -----------------------------------------
st.markdown("""
<style>
:root { --ink:#14213d; --muted:#64748b; --accent:#f59e0b; --line:#e2e8f0; }
.block-container { padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1450px; }
.hero { padding: 1.35rem 1.5rem; border-radius: 18px; color: white;
        background: linear-gradient(120deg,#14213d 0%,#1d4e66 65%,#d97706 140%); margin-bottom: 1rem; }
.hero h1 { margin: 0 0 .35rem 0; font-size: 2rem; }
.hero p { margin: 0; color: #e2e8f0; }
.kpi { border:1px solid var(--line); border-radius:14px; padding:1rem; background:rgba(148,163,184,.07); min-height:105px; }
.kpi-label { color:var(--muted); font-size:.83rem; margin-bottom:.35rem; }
.kpi-value { color:var(--ink); font-weight:750; font-size:1.55rem; }
.pill { display:inline-block; padding:.28rem .65rem; border-radius:999px; font-weight:700; font-size:.8rem; }
.pill-green { color:#166534; background:#dcfce7; } .pill-amber { color:#92400e; background:#fef3c7; }
.pill-red { color:#991b1b; background:#fee2e2; } .pill-blue { color:#1e40af; background:#dbeafe; }
.section-note { color:var(--muted); font-size:.9rem; }
div[data-testid="stTabs"] button { font-weight:650; }
footer { visibility:hidden; }
</style>
""", unsafe_allow_html=True)

# ---------------------------- Helpers -----------------------------------------
def metric_card(label, value, detail=""):
    st.markdown(
        f'<div class="kpi"><div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div><div class="section-note">{detail}</div></div>',
        unsafe_allow_html=True
    )

def pill(label, kind="blue"):
    st.markdown(f'<span class="pill pill-{kind}">{label}</span>', unsafe_allow_html=True)

def safe_json_from_text(text):
    """Extract JSON from model output even if it is wrapped in Markdown fences."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("The model did not return a JSON object.")
    return json.loads(text[start:end + 1])

def gemini_available(api_key):
    return bool(api_key and genai is not None)

def ask_gemini(api_key, prompt, image=None, history=None):
    """Call Gemini using the official google-genai SDK. Returns text or raises a useful error."""
    if not gemini_available(api_key):
        raise RuntimeError("Gemini is unavailable. Add a valid API key in the sidebar and install dependencies.")
    client = genai.Client(api_key=api_key)
    contents = []
    if history:
        for item in history:
            contents.append(types.Content(role=item["role"], parts=[types.Part.from_text(text=item["text"])]))
    parts = [types.Part.from_text(text=prompt)]
    if image is not None:
        img = image.convert("RGB")
        import io
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        parts.append(types.Part.from_bytes(data=buf.getvalue(), mime_type="image/jpeg"))
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[types.Content(role="user", parts=parts)] if not history else contents + [types.Content(role="user", parts=parts)],
        config=types.GenerateContentConfig(temperature=0.2)
    )
    if not getattr(response, "text", None):
        raise RuntimeError("Gemini returned an empty response. Try again or use a clearer image.")
    return response.text

def run_image_analysis(api_key, prompt, image, demo_data):
    if gemini_available(api_key):
        try:
            raw = ask_gemini(api_key, prompt, image=image)
            return safe_json_from_text(raw), "Gemini AI"
        except Exception as exc:
            st.warning(f"AI analysis failed; showing demonstration output instead. Details: {exc}")
    else:
        st.info("Demonstration mode: add a Gemini API key in the sidebar to analyze this image with AI.")
    return demo_data, "Demonstration"

def download_json(data, filename):
    st.download_button("⬇️ Download JSON report", data=json.dumps(data, indent=2, ensure_ascii=False),
                       file_name=filename, mime="application/json", use_container_width=False)

def inr(value):
    if value >= 1e7:
        return f"₹{value / 1e7:.2f} Cr"
    if value >= 1e5:
        return f"₹{value / 1e5:.2f} L"
    return f"₹{value:,.0f}"

def make_demo_safety():
    return {
        "safety_score": 72,
        "overall_status": "Needs Attention",
        "ppe_detection": [
            {"item": "Safety helmet", "status": "Partially observed", "notes": "Confirm all workers are wearing secured helmets."},
            {"item": "High-visibility vest", "status": "Not clearly verifiable", "notes": "Use high-visibility clothing in active work zones."},
            {"item": "Steel-toe boots", "status": "Not verifiable from image", "notes": "Verify footwear during an on-site inspection."},
            {"item": "Safety harness", "status": "Not applicable / not verifiable", "notes": "Required when working at height where fall protection applies."}
        ],
        "hazards": [
            {"hazard": "Potential unprotected edge", "severity": "High", "remedy": "Install compliant guardrails or approved fall-arrest systems; restrict access until protected."},
            {"hazard": "PPE compliance cannot be fully confirmed from one image", "severity": "Medium", "remedy": "Conduct a documented walk-through and verify PPE fit and condition."}
        ],
        "limitations": "Demonstration data only; no image inference was performed."
    }

def make_demo_crack():
    return {
        "defect_type": "Hairline",
        "estimated_crack_width_mm": 0.3,
        "confidence": "Low (demonstration)",
        "possible_root_causes": ["Drying shrinkage", "Thermal movement", "Surface coating or plaster movement"],
        "recommended_repairs": ["Measure and map the crack; record whether it is active.", "For non-structural plaster cracks, use an appropriate flexible filler after confirming the substrate.", "Have a qualified structural engineer assess any widening, diagonal, leaking, or recurring crack."],
        "urgency": "Routine inspection",
        "limitations": "Demonstration data only; width cannot be measured reliably from an unscaled photo."
    }

# ---------------------------- Sidebar -----------------------------------------
with st.sidebar:
    st.markdown("## 🏗️ Construction Intelligence")
    st.caption("Skill Wallet Capstone · Project 1")
    api_key = st.text_input(
    "Google Gemini API key",
    value=st.secrets.get("GEMINI_API_KEY", ""),
    type="password",
    help="Stored securely in Streamlit Secrets."
)
        st.success("API key entered for this session")
    else:
        st.info("Demo mode is available without an API key.")
    st.divider()
    st.markdown("### Architecture overview")
    st.markdown("""
    **Streamlit UI** → input validation → **Gemini multimodal API** (optional) → structured results → JSON export.

    - Stateless; no external database
    - Local session state for chat
    - Images processed in-memory
    - Demo fixtures for offline preview
    """)
    st.divider()
    st.markdown("### Feature navigation")
    st.markdown("1. Site Safety & PPE Audit\n2. Crack Diagnostics\n3. Planning & Valuation\n4. Site Assistant")
    st.caption("For decision support only. Not a substitute for a competent safety officer, licensed structural engineer, quantity surveyor, or local authority.")

# ---------------------------- Header ------------------------------------------
st.markdown(f"""
<div class="hero">
  <h1>🏗️ {APP_TITLE}</h1>
  <p>AI-assisted site safety, concrete diagnostics, project planning and weather-aware guidance.</p>
</div>
""", unsafe_allow_html=True)
st.caption(f"Session date: {datetime.now().strftime('%d %b %Y')} · AI model: {MODEL_NAME if api_key else 'Demonstration mode'}")
st.warning("Safety and structural outputs are preliminary visual guidance. Image-only estimates can be wrong; do not use this app to certify compliance, diagnose structural safety, or replace professional inspection.")

tab_safety, tab_crack, tab_plan, tab_assistant = st.tabs([
    "🦺 Site Safety & PPE Audit", "🧱 Crack Diagnostics", "📐 Planning & Valuation", "🌦️ Daily Site Assistant"
])

# ---------------------------- Tab 1: Safety -----------------------------------
with tab_safety:
    st.subheader("Site Safety & PPE Audit")
    st.markdown("Upload a clear construction-site photo. The analysis is visual triage only; standards and site context must be verified by a competent person.")
    safety_file = st.file_uploader("Upload site photo", type=["jpg", "jpeg", "png"], key="safety_upload")
    if safety_file:
        try:
            safety_image = Image.open(safety_file)
            st.image(safety_image, caption="Uploaded site photo", use_container_width=True)
            if st.button("Analyze PPE & hazards", type="primary", key="analyze_safety"):
                prompt = """
You are a cautious construction-site visual audit assistant. Analyze the supplied photo only; do not claim certainty where an item is occluded or not visible. Use OSHA guidance and relevant Indian construction/site-safety practices as context, but do NOT claim that IS 456 is a PPE standard (IS 456 concerns plain and reinforced concrete). Return ONLY valid JSON with:
{
 "safety_score": integer 0-100,
 "overall_status": "Compliant"|"Needs Attention"|"Unsafe"|"Unable to Determine",
 "ppe_detection": [{"item":"Safety helmet","status":"Observed"|"Not observed"|"Partially observed"|"Not verifiable"|"Not applicable","notes":"..."}],
 "hazards": [{"hazard":"...","severity":"Low"|"Medium"|"High"|"Critical","remedy":"..."}],
 "limitations":"..."
}
Include exactly these PPE items: safety helmet, high-visibility vest, steel-toe boots, safety harness. Assess harness only if work at height/fall risk is visible; otherwise not applicable/not verifiable. List only visible or reasonably indicated hazards, distinguish observations from assumptions, and do not infer hidden footwear. If the image is unclear, use Unable to Determine and explain. This is not a formal compliance certification.
"""
                demo = make_demo_safety()
                with st.spinner("Reviewing site image..."):
                    result, mode = run_image_analysis(api_key, prompt, safety_image, demo)
                st.session_state["safety_result"] = result
                st.session_state["safety_mode"] = mode
        except Exception as exc:
            st.error(f"Could not open this image: {exc}")
    result = st.session_state.get("safety_result")
    if result:
        st.divider()
        st.markdown(f"#### Results · {st.session_state.get('safety_mode','Unknown mode')}")
        score = result.get("safety_score", "—")
        status = str(result.get("overall_status", "Unable to Determine"))
        c1, c2, c3 = st.columns(3)
        with c1: metric_card("Safety score", f"{score}/100", "Indicative visual score only")
        with c2: metric_card("Overall status", status, "Requires human verification")
        with c3: metric_card("Hazards identified", len(result.get("hazards", [])), "Based on visible evidence")
        kind = "green" if status.lower() == "compliant" else "red" if status.lower() == "unsafe" else "amber"
        pill(status, kind)
        st.markdown("#### PPE checklist")
        ppe = result.get("ppe_detection", [])
        if ppe:
            st.dataframe(ppe, use_container_width=True, hide_index=True)
        else:
            st.info("No PPE checklist returned.")
        st.markdown("#### Hazards & corrective actions")
        hazards = result.get("hazards", [])
        if hazards:
            for h in hazards:
                severity = str(h.get("severity", "Medium"))
                k = "red" if severity in ("High", "Critical") else "amber" if severity == "Medium" else "green"
                with st.container(border=True):
                    pill(severity, k)
                    st.markdown(f"**{h.get('hazard','Hazard')}**")
                    st.write(h.get("remedy", "Obtain qualified site review."))
        else:
            st.success("No hazards were returned; this does not prove the site is hazard-free.")
        if result.get("limitations"):
            st.caption("Limitations: " + str(result["limitations"]))
        download_json(result, "site_safety_audit.json")

# ---------------------------- Tab 2: Crack diagnostics -------------------------
with tab_crack:
    st.subheader("Crack Diagnostics & Structural Integrity")
    st.markdown("Upload a surface photo. A width estimate from a photo is unreliable unless a scale is present; treat the output as a triage prompt, not a structural diagnosis.")
    crack_file = st.file_uploader("Upload concrete / wall photo", type=["jpg", "jpeg", "png"], key="crack_upload")
    if crack_file:
        try:
            crack_image = Image.open(crack_file)
            st.image(crack_image, caption="Uploaded surface photo", use_container_width=True)
            if st.button("Assess visible defect", type="primary", key="analyze_crack"):
                prompt = """
Act as a cautious visual assistant for concrete and wall defect triage. Return ONLY valid JSON:
{
 "defect_type":"Hairline"|"Settlement"|"Structural Shear"|"Thermal Expansion"|"Spalling"|"Unable to Determine",
 "estimated_crack_width_mm": number|null,
 "confidence":"Low"|"Medium"|"High",
 "possible_root_causes":["..."],
 "recommended_repairs":["..."],
 "urgency":"Routine inspection"|"Prompt engineer review"|"Urgent - restrict area and obtain engineer assessment",
 "limitations":"..."
}
Do not present a photo-derived width as a measurement; if there is no scale reference, return null or a clearly labelled rough estimate with low confidence. Explain uncertainty and recommend qualified structural engineering review for diagonal/stepped cracks, widening cracks, exposed reinforcement, displacement, water ingress, or signs of distress. Repairs such as epoxy injection or structural re-grouting must only be recommended conditionally after a professional determines the cause and whether the crack is active. Never certify structural integrity.
"""
                with st.spinner("Assessing visible defect..."):
                    result, mode = run_image_analysis(api_key, prompt, crack_image, make_demo_crack())
                st.session_state["crack_result"] = result
                st.session_state["crack_mode"] = mode
        except Exception as exc:
            st.error(f"Could not open this image: {exc}")
    result = st.session_state.get("crack_result")
    if result:
        st.divider()
        st.markdown(f"#### Assessment · {st.session_state.get('crack_mode','Unknown mode')}")
        c1, c2, c3 = st.columns(3)
        with c1: metric_card("Defect classification", result.get("defect_type", "Unknown"), "Visual hypothesis")
        with c2:
            width = result.get("estimated_crack_width_mm")
            metric_card("Estimated width", f"{width} mm" if width is not None else "Not estimated", "Not a calibrated measurement")
        with c3: metric_card("Urgency", result.get("urgency", "Unknown"), "Follow qualified advice")
        st.markdown("**Possible root causes**")
        for cause in result.get("possible_root_causes", []): st.markdown(f"- {cause}")
        st.markdown("**Recommended next steps / repairs**")
        for repair in result.get("recommended_repairs", []): st.markdown(f"- {repair}")
        st.caption(f"Confidence: {result.get('confidence','Not provided')}. {result.get('limitations','')}")
        download_json(result, "crack_diagnostics.json")

# ---------------------------- Tab 3: Planning ---------------------------------
with tab_plan:
    st.subheader("Planning & Real Estate Valuation")
    st.markdown("Use these transparent planning assumptions for an early estimate. Replace rates and quantities with local BOQ, structural design and current supplier quotations.")
    left, right = st.columns([1, 1.25], gap="large")
    with left:
        structure = st.selectbox("Structure type", ["Residential house", "Apartment building", "Commercial building", "Warehouse / industrial", "Institutional building"])
        area = st.number_input("Built-up area (sq ft)", min_value=100, max_value=2_000_000, value=1800, step=100)
        tier = st.selectbox("Location tier", ["Tier 1", "Tier 2", "Tier 3"])
        completion = st.slider("Completion percentage", min_value=0, max_value=100, value=35, step=5)
        custom_rate = st.number_input("Estimated construction rate (₹ / sq ft)", min_value=500, max_value=15000, value={"Tier 1":2600,"Tier 2":2100,"Tier 3":1750}[tier], step=100,
                                       help="Editable rate; location tier does not automatically override your custom rate.")
        land_value = st.number_input("Estimated land value (₹, optional)", min_value=0, max_value=2_000_000_000, value=0, step=100000)
    with right:
        # Approximate planning coefficients, not a quantity survey or design.
        total_budget = area * custom_rate
        incurred = total_budget * completion / 100
        # Illustrative asset uplift factor varies by tier; land value is kept separate.
        market_factor = {"Tier 1": 1.20, "Tier 2": 1.12, "Tier 3": 1.05}[tier]
        asset_value = total_budget * market_factor * (0.35 + 0.65 * completion / 100) + land_value
        cement_bags = area * 0.40
        steel_kg = area * 4.0
        st.markdown("#### Project estimate")
        a,b = st.columns(2)
        with a: metric_card("Estimated construction budget", inr(total_budget), f"{area:,} sq ft × ₹{custom_rate:,}/sq ft")
        with b: metric_card("Estimated capex incurred", inr(incurred), f"{completion}% of construction budget")
        a,b = st.columns(2)
        with a: metric_card("Indicative asset valuation", inr(asset_value), "Heuristic estimate incl. optional land value")
        with b: metric_card("Progress milestone", f"{completion}%", "Construction completion input")
        st.progress(completion / 100)
        st.markdown("#### Indicative material quantities")
        a,b = st.columns(2)
        with a: metric_card("Cement", f"{cement_bags:,.0f} bags", "Planning factor: 0.40 bags/sq ft")
        with b: metric_card("Reinforcement steel", f"{steel_kg/1000:,.2f} tonnes", "Planning factor: 4 kg/sq ft")
        st.caption("Material coefficients vary significantly by structural system, spans, loads, foundation, specifications and wastage. Validate with drawings and a quantity surveyor.")
    st.markdown("#### Conceptual 3D architectural rendering")
    default_prompt = f"Conceptual architectural visualization of a {structure.lower()}, {area:,} square feet built-up area, contemporary Indian context, {tier} city, realistic daylight, professional architectural render, no text, not a construction drawing"
    render_prompt = st.text_area("Image prompt (editable)", value=default_prompt, height=90)
    encoded_prompt = quote(render_prompt.strip())
    render_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=768&model=flux&nologo=true"
    st.link_button("Open conceptual rendering (Pollinations AI)", render_url, help="Opens a third-party image generation service. Availability and terms are controlled by that service.")
    st.caption("The rendering is conceptual only, not an engineered drawing, permit submission, or representation of buildable dimensions.")
    plan_report = {
        "structure_type": structure, "built_up_area_sqft": area, "location_tier": tier,
        "construction_rate_inr_per_sqft": custom_rate, "completion_percent": completion,
        "estimated_construction_budget_inr": round(total_budget),
        "estimated_capex_incurred_inr": round(incurred),
        "indicative_asset_valuation_inr": round(asset_value), "optional_land_value_inr": land_value,
        "estimated_cement_bags": round(cement_bags), "estimated_reinforcement_steel_kg": round(steel_kg),
        "assumptions": ["Illustrative rate and material coefficients only.", "Asset value is a heuristic, not a formal valuation.", "Validate with local BOQ, drawings, market data and qualified professionals."]
    }
    download_json(plan_report, "project_planning_estimate.json")

# ---------------------------- Tab 4: Assistant --------------------------------
with tab_assistant:
    st.subheader("Daily Site Assistant & Weather-Aware Advisory")
    weather = st.selectbox("Current / forecast site condition", ["Normal", "High Wind", "Heavy Rain", "Extreme Heat"])
    advisories = {
        "Normal": ("Routine controls", "Continue only with the approved method statement, toolbox talks, PPE, housekeeping, equipment checks and local forecast monitoring.", "blue"),
        "High Wind": ("Wind / lifting risk", "Pause crane and suspended-load operations when wind exceeds the equipment/manufacturer/site lift-plan limits. Secure loose materials, stop exposed-height work when unsafe, and follow the site emergency plan.", "red"),
        "Heavy Rain": ("Water ingress / electrical risk", "Assess flooding, excavation stability and access routes. Isolate damaged or water-exposed electrical equipment through authorized personnel; use protected power distribution and do not enter flooded electrical areas. Review concrete placement and curing with the engineer.", "red"),
        "Extreme Heat": ("Heat stress risk", "Provide potable water, shaded rest, acclimatization and work-rest cycles; monitor workers for heat illness and activate emergency response if symptoms occur. Protect fresh concrete and follow the approved curing specification.", "amber")
    }
    title, message, kind = advisories[weather]
    st.markdown(f"### {title}")
    pill("Priority advisory", kind)
    st.info(message)
    st.caption("Use the site-specific risk assessment, equipment limits, local weather alerts and competent-person instructions. This advisory is general guidance, not a live weather feed.")
    st.divider()
    st.markdown("#### Ask the construction assistant")
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    for item in st.session_state.chat_history:
        with st.chat_message(item["role"]):
            st.markdown(item["content"])
    user_question = st.chat_input("Ask about method statements, materials, safety, planning...")
    if user_question:
        st.session_state.chat_history.append({"role": "user", "content": user_question})
        with st.chat_message("user"):
            st.markdown(user_question)
        system_prompt = f"""You are a cautious construction engineering information assistant. Current selected weather condition: {weather}.
Provide practical, clearly qualified general information. Do not certify structural safety, replace local codes, invent live weather data, or provide definitive structural design calculations. Ask clarifying questions where needed. For high-risk situations, direct the user to a competent site safety officer or licensed engineer. Distinguish Indian context from OSHA context when relevant. User question: {user_question}"""
        answer = None
        if gemini_available(api_key):
            try:
                # Keep recent conversation context, mapping Streamlit roles to Gemini roles.
                history = []
                for entry in st.session_state.chat_history[-8:-1]:
                    history.append({"role": "model" if entry["role"] == "assistant" else "user", "text": entry["content"]})
                answer = ask_gemini(api_key, system_prompt, history=history)
            except Exception as exc:
                st.warning(f"Gemini request failed; returning a fallback response. Details: {exc}")
        if not answer:
            answer = ("**Demonstration assistant:** I can help outline general construction concepts, inspection checklists, material planning and safety questions. "
                      "For this specific question, verify the relevant drawings, approved method statement and local regulations with the responsible site engineer. "
                      "If there is an immediate hazard, stop the affected work and follow the site's emergency procedure.")
        st.session_state.chat_history.append({"role": "assistant", "content": answer})
        with st.chat_message("assistant"):
            st.markdown(answer)
    if st.button("Clear chat history", key="clear_chat"):
        st.session_state.chat_history = []
        st.rerun()

st.divider()
st.caption("Multimodal Construction Intelligence Platform · Skill Wallet Capstone Project 1 · Built with Streamlit and optional Google Gemini API.")
