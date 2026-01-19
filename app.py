import streamlit as st
import pandas as pd
import time
import os


try:
    from auth import login
    from utils.router import choose_models
    from utils.parallel import run_parallel
    from utils.rate_limiter import check_limit
    from utils.report import generate_report
except Exception as e:
    st.error(e)
    st.stop()

st.set_page_config(
    page_title="LLM Nexus",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------- UI STYLES ONLY --------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background-color: #020617;
    color: #e5e7eb;
}

/* Headings */
.app-title {
    font-size: 2.6rem;
    font-weight: 700;
    color: #e5e7eb;
}
.app-subtitle {
    color: #9ca3af;
    margin-bottom: 2rem;
}

/* Cards */
.card {
    background: #020617;
    border: 1px solid #1f2937;
    border-radius: 14px;
    padding: 20px;
}

/* Inputs */
textarea, div[data-baseweb="select"] > div {
    background-color: #020617 !important;
    border: 1px solid #1f2937 !important;
    border-radius: 10px !important;
    color: #e5e7eb !important;
}
textarea:focus {
    border-color: #7dd3fc !important;
    box-shadow: 0 0 0 1px rgba(125, 211, 252, 0.35);
}

/* Buttons */
div.stButton > button {
    background: linear-gradient(135deg, #7dd3fc, #60a5fa);
    color: #020617;
    border: none;
    border-radius: 10px;
    padding: 0.8rem;
    font-weight: 600;
    width: 100%;
    transition: all 0.2s ease;
}
div.stButton > button:hover {
    filter: brightness(1.05);
}

/* Model result card */
.model-card {
    border: 1px solid #1f2937;
    border-radius: 14px;
    padding: 18px;
    background-color: #020617;
    height: 100%;
}

/* Model title */
.model-title {
    font-size: 0.85rem;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: #7dd3fc;
    font-weight: 700;
    margin-bottom: 10px;
}

/* Metrics */
div[data-testid="metric-container"] {
    background-color: #020617;
    border: 1px solid #1f2937;
    border-radius: 10px;
    padding: 12px;
}
</style>
""", unsafe_allow_html=True)

# -------------------- SIDEBAR --------------------
with st.sidebar:
    st.markdown("## ⚙️ Control Panel")

    if "user" in st.session_state:
        st.success(f"👤 {st.session_state.user}")

    st.divider()
    st.markdown("### Model Settings")

    model_temp = st.slider("Temperature", 0.0, 1.0, 0.7)
    max_tokens = st.number_input("Max Tokens", value=1024, step=256)

    st.divider()
    st.caption("LLM Nexus • Enterprise v2.1.0")

# -------------------- MAIN --------------------
def main():
    login()
    if "user" not in st.session_state:
        st.stop()

    st.markdown('<div class="app-title">⚡ LLM Nexus</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="app-subtitle">Enterprise-grade model routing & cost intelligence.</div>',
        unsafe_allow_html=True
    )

    col_left, col_right = st.columns([1, 3])

    with col_left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        task = st.selectbox(
            "Target Objective",
            ["General", "Coding", "Fast Response", "Cost Saving"]
        )
        st.metric("Active Models", "3", "Operational")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        prompt = st.text_area(
            "Input Prompt",
            height=160,
            placeholder="Write a secure Python function to connect to AWS S3..."
        )
        st.markdown('</div>', unsafe_allow_html=True)

    st.write("")
    run_btn = st.button("🚀 Run Analysis")

    if run_btn:
        if not check_limit(st.session_state.user):
            st.error("Rate limit reached.")
            st.stop()

        if not prompt.strip():
            st.warning("Please enter a prompt.")
            st.stop()

        with st.status("Running model orchestration...", expanded=True):
            models = choose_models(task)
            start = time.time()
            responses = run_parallel(prompt, models)
            elapsed = round(time.time() - start, 2)

        st.markdown("## 📊 Results")

        tab1, tab2, tab3, tab4 = st.tabs([
            "Visual",
            "Raw JSON",
            "Cost",
            "Performance"
        ])

        with tab1:
            cols = st.columns(len(responses))
            for i, (model, text) in enumerate(responses.items()):
                with cols[i]:
                    st.markdown(
                        f"""
                        <div class="model-card">
                            <div class="model-title">{model}</div>
                            {text}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

        with tab2:
            st.json(responses)

        with tab3:
            generate_report(prompt, responses)
            st.success("Cost report generated.")
            c1, c2 = st.columns(2)
            c1.metric("Estimated Cost", "$0.0042", "-12%")
            c2.metric("Avg Latency", f"{elapsed}s", "Fast")

        with tab4:
            metrics_file = "data/metrics/metrics.csv"
            if not os.path.exists(metrics_file):
                st.warning("No metrics available.")
            else:
                df = pd.read_csv(metrics_file)
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")

                st.bar_chart(df.groupby("model")["latency"].mean())
                st.bar_chart(df.groupby("model")["response_length"].mean())
                st.line_chart(df.set_index("timestamp").resample("1min").count()["model"])


if __name__ == "__main__":
    main()
