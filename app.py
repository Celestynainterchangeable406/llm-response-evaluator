import streamlit as st
import pandas as pd
import json
from datetime import datetime
from evaluator import score_responses, get_recommendation

st.set_page_config(
    page_title="LLM Response Evaluator",
    page_icon="🧠",
    layout="wide"
)

st.markdown("""
    <style>
    .main { background-color: #0f0f0f; color: #f0f0f0; }
    .stTextArea textarea { background-color: #1a1a1a; color: #f0f0f0; }
    .metric-card {
        background: #1a1a1a;
        border: 1px solid #333;
        border-radius: 8px;
        padding: 16px;
        margin: 8px 0;
    }
    .winner-badge {
        background: #00c853;
        color: black;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 14px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🧠 LLM Response Quality Evaluator")
st.markdown("*Evaluate and compare LLM responses across 5 quality dimensions — inspired by real RLHF post-training workflows*")
st.divider()

# --- Input Section ---
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    prompt = st.text_area("📝 User Prompt", placeholder="Enter the prompt given to the model...", height=100)
with col2:
    turn_number = st.selectbox("Turn Number", list(range(1, 9)), index=0)
with col3:
    prompt_type = st.selectbox("Prompt Type", ["Instructional", "Conversational", "Technical", "Creative", "Factual"])

col_a, col_b = st.columns(2)
with col_a:
    st.subheader("Response A")
    response_a = st.text_area("", placeholder="Paste Response A here...", height=200, key="resp_a")
with col_b:
    st.subheader("Response B")
    response_b = st.text_area("", placeholder="Paste Response B here...", height=200, key="resp_b")

st.divider()

# --- Manual Scoring Section ---
st.subheader("📊 Rate Each Dimension (1-5)")

dimensions = [
    ("instruction_following", "🎯 Instruction Following", "Does the response follow all instructions given in the prompt?"),
    ("truthfulness", "✅ Truthfulness", "Is the response factually accurate and honest?"),
    ("prompt_correctness", "🔍 Prompt Correctness", "Does the response correctly address what was asked?"),
    ("writing_quality", "✍️ Writing Quality", "Is the response well-written, clear, and coherent?"),
    ("verbosity", "📏 Verbosity", "Is the length appropriate — not too short, not too long?"),
]

scores_a = {}
scores_b = {}

for key, label, help_text in dimensions:
    c1, c2, c3 = st.columns([3, 2, 2])
    with c1:
        st.markdown(f"**{label}**")
        st.caption(help_text)
    with c2:
        scores_a[key] = st.slider(f"A", 1, 5, 3, key=f"a_{key}")
    with c3:
        scores_b[key] = st.slider(f"B", 1, 5, 3, key=f"b_{key}")

notes = st.text_area("🗒️ Observations (optional)", placeholder="Any interesting patterns or notable differences you noticed...", height=80)

st.divider()

if st.button("⚡ Generate Evaluation Report", type="primary", use_container_width=True):
    if not prompt or not response_a or not response_b:
        st.error("Please fill in the prompt and both responses.")
    else:
        result = score_responses(scores_a, scores_b)
        recommendation = get_recommendation(result, scores_a, scores_b)

        st.success("✅ Evaluation Complete!")
        st.subheader("📈 Results")

        # Score Summary
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Response A — Total Score", f"{result['total_a']} / 25")
        with col2:
            st.metric("Response B — Total Score", f"{result['total_b']} / 25")
        with col3:
            winner = "A" if result['total_a'] > result['total_b'] else ("B" if result['total_b'] > result['total_a'] else "Tie")
            st.metric("Winner", f"Response {winner}" if winner != "Tie" else "Tie")

        # Dimension breakdown table
        st.subheader("Dimension Breakdown")
        dim_labels = [d[1] for d in dimensions]
        dim_keys = [d[0] for d in dimensions]
        df = pd.DataFrame({
            "Dimension": dim_labels,
            "Score A": [scores_a[k] for k in dim_keys],
            "Score B": [scores_b[k] for k in dim_keys],
            "Winner": ["A" if scores_a[k] > scores_b[k] else ("B" if scores_b[k] > scores_a[k] else "Tie") for k in dim_keys]
        })
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Recommendation
        st.subheader("💡 Recommendation")
        st.info(recommendation)

        # Save to log
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "turn": turn_number,
            "prompt_type": prompt_type,
            "prompt": prompt,
            "scores_a": scores_a,
            "scores_b": scores_b,
            "total_a": result['total_a'],
            "total_b": result['total_b'],
            "winner": winner,
            "weakest_dimension_a": result['weakest_a'],
            "weakest_dimension_b": result['weakest_b'],
            "notes": notes
        }

        # Append to JSONL log
        with open("evaluation_log.jsonl", "a") as f:
            f.write(json.dumps(log_entry) + "\n")

        st.caption("✅ Entry saved to evaluation_log.jsonl")

        # Download button
        df_export = pd.DataFrame([log_entry])
        csv = df_export.to_csv(index=False)
        st.download_button("📥 Download This Entry as CSV", csv, "evaluation_entry.csv", "text/csv")

st.divider()

# --- Log Viewer ---
st.subheader("📋 Evaluation History")
try:
    with open("evaluation_log.jsonl", "r") as f:
        entries = [json.loads(line) for line in f.readlines()]
    if entries:
        df_log = pd.DataFrame(entries)[["timestamp", "turn", "prompt_type", "total_a", "total_b", "winner", "weakest_dimension_a", "weakest_dimension_b", "notes"]]
        st.dataframe(df_log, use_container_width=True, hide_index=True)

        # Pattern insights
        if len(entries) >= 5:
            st.subheader("🔍 Pattern Insights")
            df_all = pd.DataFrame(entries)
            winner_counts = df_all['winner'].value_counts()
            st.write(f"**Response Win Rate:** A wins {winner_counts.get('A', 0)} times, B wins {winner_counts.get('B', 0)} times")

            weakest = pd.Series([e['weakest_dimension_a'] for e in entries] + [e['weakest_dimension_b'] for e in entries])
            st.write(f"**Most Commonly Weak Dimension:** {weakest.value_counts().idxmax()}")

            turn_data = df_all.groupby('turn')[['total_a', 'total_b']].mean()
            st.write("**Average Score by Turn:**")
            st.bar_chart(turn_data)
    else:
        st.info("No evaluations logged yet. Run your first evaluation above.")
except FileNotFoundError:
    st.info("No evaluations logged yet. Run your first evaluation above.")
