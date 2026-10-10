"""Streamlit interface for the Contract Guard FastAPI service."""

import json
import os
import time

import requests
import streamlit as st


st.set_page_config(
    page_title="Contract Guard",
    page_icon="🛡️",
    layout="wide",
)


def get_api_base_url() -> str:
    """Read the backend URL from Streamlit secrets or the local environment."""
    try:
        configured_url = st.secrets.get("API_BASE_URL", "")
    except (FileNotFoundError, AttributeError):
        configured_url = ""
    return (configured_url or os.getenv("API_BASE_URL", "http://localhost:8000")).rstrip("/")


API_BASE_URL = get_api_base_url()


def api_error_message(error: requests.RequestException) -> str:
    response = getattr(error, "response", None)
    if response is not None:
        try:
            detail = response.json().get("detail")
        except (ValueError, AttributeError):
            detail = None
        if detail:
            return str(detail)
    return str(error)


def analyze_pdf(filename: str, file_bytes: bytes) -> dict:
    """Submit a PDF and poll the backend until the analysis is ready."""
    upload_response = requests.post(
        f"{API_BASE_URL}/api/upload",
        files={"file": (filename, file_bytes, "application/pdf")},
        timeout=120,
    )
    upload_response.raise_for_status()
    job_id = upload_response.json()["job_id"]

    progress = st.progress(0, text="Starting analysis…")
    deadline = time.monotonic() + 15 * 60

    while time.monotonic() < deadline:
        status_response = requests.get(
            f"{API_BASE_URL}/api/status/{job_id}", timeout=30
        )
        status_response.raise_for_status()
        status = status_response.json()
        percent = int(status.get("progress", 0))
        progress.progress(
            min(max(percent, 0), 100),
            text=status.get("step", "Analyzing contract…"),
        )

        if status.get("status") == "completed":
            progress.empty()
            return status["result"]
        if status.get("status") == "failed":
            progress.empty()
            raise RuntimeError(status.get("error") or "Contract analysis failed.")

        time.sleep(2)

    progress.empty()
    raise TimeoutError("Analysis is taking longer than expected. Please try again.")


def render_analysis(result: dict) -> None:
    summary = result.get("risk_summary", {})
    st.subheader(result.get("document_name", "Contract analysis"))

    metrics = st.columns(5)
    metrics[0].metric("Overall risk", f"{summary.get('overall_risk_score', 0):.0f}/100")
    metrics[1].metric("Clauses", summary.get("total_clauses", 0))
    metrics[2].metric("High risk", summary.get("high_risk", 0))
    metrics[3].metric("Medium risk", summary.get("medium_risk", 0))
    metrics[4].metric("Low risk", summary.get("low_risk", 0))

    distribution = summary.get("risk_distribution", {})
    if distribution:
        st.markdown("#### Risk distribution")
        st.bar_chart(
            {
                "Risk level": list(distribution.keys()),
                "Share (%)": list(distribution.values()),
            },
            x="Risk level",
            y="Share (%)",
        )

    clauses = result.get("clauses", [])
    risk_filter = st.selectbox("Filter clauses by risk", ["All", "HIGH", "MEDIUM", "LOW"])
    visible_clauses = [
        clause for clause in clauses
        if risk_filter == "All" or clause.get("risk_level") == risk_filter
    ]

    st.markdown(f"#### Clauses ({len(visible_clauses)})")
    for clause in visible_clauses:
        level = clause.get("risk_level", "LOW")
        title = f"{level} · {clause.get('clause_type', 'Uncategorized')}"
        if clause.get("section_heading"):
            title += f" · {clause['section_heading']}"
        with st.expander(title):
            st.write(clause.get("text", ""))
            if clause.get("explanation"):
                st.markdown("**Explanation**")
                st.write(clause["explanation"])
            if clause.get("risks"):
                st.markdown("**Potential risks**")
                for risk in clause["risks"]:
                    st.markdown(f"- {risk}")
            if clause.get("recommendations"):
                st.markdown("**Recommendations**")
                for recommendation in clause["recommendations"]:
                    st.markdown(f"- {recommendation}")
            if clause.get("suggested_rewrite"):
                st.markdown("**Suggested rewrite**")
                st.write(clause["suggested_rewrite"])
            related_cases = clause.get("related_cases", [])
            if related_cases:
                st.markdown("**Related cases**")
                for case in related_cases:
                    st.markdown(f"- **{case.get('case_name', 'Case')}** — {case.get('summary', '')}")

    st.download_button(
        "Download analysis as JSON",
        data=json.dumps(result, indent=2),
        file_name="contract-analysis.json",
        mime="application/json",
    )


st.title("🛡️ Contract Guard")
st.caption("Upload a contract PDF to identify clauses that may need closer review.")

with st.sidebar:
    st.header("Connection")
    st.code(API_BASE_URL, language=None)
    try:
        health_response = requests.get(f"{API_BASE_URL}/api/health", timeout=10)
        health_response.raise_for_status()
        health = health_response.json()
        st.success("Backend connected")
        st.caption("Gemini explanations: " + ("enabled" if health.get("gemini_configured") else "not configured"))
    except requests.RequestException as error:
        st.error("Backend unavailable")
        st.caption(api_error_message(error))

uploaded_file = st.file_uploader("Choose a contract PDF", type=["pdf"])
if uploaded_file is not None:
    st.caption(f"{uploaded_file.name} · {uploaded_file.size / (1024 * 1024):.1f} MB")
    if uploaded_file.size > 50 * 1024 * 1024:
        st.error("The PDF exceeds the backend's 50 MB upload limit.")
    elif st.button("Analyze contract", type="primary"):
        try:
            with st.spinner("Submitting contract…"):
                result = analyze_pdf(uploaded_file.name, uploaded_file.getvalue())
            st.session_state["analysis_result"] = result
        except (requests.RequestException, RuntimeError, TimeoutError) as error:
            st.error(api_error_message(error) if isinstance(error, requests.RequestException) else str(error))

if st.session_state.get("analysis_result"):
    st.divider()
    render_analysis(st.session_state["analysis_result"])
