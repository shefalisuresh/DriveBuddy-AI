import streamlit as st
import pyodbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from groq import Groq  # import Groq client
from risk_score_calc import generate_csv

try:
    csv_file = generate_csv()  # runs inside the same Python environment
    st.success(f"CSV generated successfully: {csv_file}")
except Exception as e:
    st.error(f"Failed to generate CSV: {e}")

# ---------------------------------------
# 🌐 Page Config
# ---------------------------------------
st.set_page_config(page_title="Risk Score Dashboard", layout="wide")

# Custom CSS styling
st.markdown("""
    <style>
    .main {
        background: linear-gradient(135deg, #f7f9fc 0%, #eef2f7 100%);
        padding: 2rem;
        border-radius: 12px;
    }
    h1 {
        text-align: center;
        color: #1a237e;
        font-family: 'Segoe UI', sans-serif;
    }
    .stDataFrame {
        border-radius: 12px !important;
        overflow: hidden !important;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------
# Initialize Groq client
# ---------------------------------------
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# ---------------------------------------
# 1️⃣ Database Connection
# ... (your existing init_connection, run_query, etc.)

# ---------------------------------------
# 3️⃣ Load Policy Transactions
# ---------------------------------------
policy_file_path = "PolicyTransactions.csv"
policy_df = pd.read_csv(policy_file_path)
policy_df = policy_df[['POL_NO', 'POL_EFF_DT', 'TRANS_CD', 'WRITTEN_PREM_AMT', 'COVG_CD']]

# ---------------------------------------
# Sidebar
# ---------------------------------------
st.sidebar.image("https://www.insurtechexpress.com/wp-content/uploads/2023/11/iStock-1153620019-scaled-1.jpg", width=200)
st.sidebar.title("Policy Risk Insights")
st.sidebar.markdown("Explore driver risk patterns and trends.")
st.sidebar.markdown("---")

# ---------------------------------------
# Main Layout & Insurance Image
# ---------------------------------------
# show a banner image relevant to insurance / risk / driving
st.image(
    "https://as2.ftcdn.net/v2/jpg/05/15/30/57/1000_F_515305790_58wwwoB0DbvAidgDZbK7U3ZPhUvvfjzy.jpg",
    caption="Driving / Insurance Risk Monitoring",
    width=600  # set width in pixels; height scales to preserve aspect ratio
)

st.markdown("<h1>Policy & Driver Risk Dashboard</h1>", unsafe_allow_html=True)

policy_input = st.text_input("Enter Policy Number to Analyze:", placeholder="e.g. 3996585786")

if st.button("Analyze Policy"):
    policy_input = policy_input.strip()
    if not policy_input:
        st.warning("Please enter a valid policy number.")
    else:
        filtered_df = policy_df[policy_df["POL_NO"].astype(str) == policy_input]

        if filtered_df.empty:
            st.error(f"No records found for Policy Number: {policy_input}")
        else:
            st.success(f"Policy {policy_input} Found!")
            st.subheader("Policy Details")
            st.dataframe(filtered_df, use_container_width=True)

            # Fetch Driver Metrics
            # Load the full context fusion CSV once at the start
            context_df = pd.read_csv("fleet_context_fusion.csv")

            # Filter for the selected policy number
            driver_df = context_df[context_df["policy_number"].astype(str) == policy_input]

            # Convert timestamp column to datetime if needed
            driver_df["timestamp"] = pd.to_datetime(driver_df["timestamp"])


            if driver_df.empty:
                st.warning("No Driver Metrics found for this policy.")
            else:
                driver_df["timestamp"] = pd.to_datetime(driver_df["timestamp"])

                # → **AI Summary Section**
                # Build messages for the model
                # include a system message instructing behavior
                messages = [
    {
        "role": "system",
        "content": (
            "You are a risk analytics assistant for vehicle insurance. "
            "You analyze driver telematics data and policy transactions to produce clear, accurate risk insights. "
            "You must summarize driver risk trends, anomalies, and possible causes concisely. "
            "Then, calculate updated insurance premiums only for applicable coverages like Personal Automobile Liability Coverage (exclude other coverages). "
            "Use consistent percentage adjustments across text and tables. "
            "If the driver's risk is low, apply discounts (negative adjustments); if high, apply penalties (positive adjustments). "
            "Ensure that the final premium summary table exactly matches the calculations described in the text. "
            "The table must include: Coverage, Base Rate, Risk Adjustment (%), Stress/Fatigue Adjustment (%), and Final Premium ($). "
            "Finally, provide a short human-readable explanation of the overall driver risk profile and premium justification. Please don't show any python script to calculate premiums"
            "Present all calculations step-by-step in a clear, structured, human-readable format. "
            "Use consistent numeric formatting and avoid mixing up numbers with calculations. "
        )
    },
    {
        "role": "user",
        "content": (
            f"Here is the recent driver metrics data for policy {policy_input} (last 100 rows):\n"
            + driver_df.tail(100)[['timestamp', 'risk_score', 'speed', 'stress_level', 'fatigue', 'event']].to_string(index=False)
            + "\n\nPolicy Transactions (last 30 rows):\n"
            + filtered_df.tail(30)[['POL_NO', 'POL_EFF_DT', 'TRANS_CD', 'WRITTEN_PREM_AMT', 'COVG_CD']].to_string(index=False)
            + "\n\nInstructions:\n"
            "- Summarize driver risk trends and anomalies clearly.\n"
            "- Identify possible causes for risky behavior.\n"
            "- Apply risk-based premium adjustments as follows:\n"
            "   * Risk Adjustment → +10% if avg risk_score > 0.5, -5% if < 0.3.\n"
            "   * Stress/Fatigue Adjustment → +15% if avg stress > 40 or fatigue > 30, -5% if both < 20.\n"
            "- Only include Personal Automobile Liability Coverage in the premium table.\n"
            "- Display the final results in a professional, structured report with:\n"
            "   • Risk Trends Summary\n"
            "   • Anomalies and Possible Causes\n"
            "   • Premium Calculation Steps\n"
            "   • Premium Summary Table\n"
            "   • Final Remarks or Recommendations"
        )
    }
]




                # Call Groq model
                try:
                    chat_resp = client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=messages,
                        temperature=0.2
                    )
                    ai_summary = chat_resp.choices[0].message.content
                except Exception as e:
                    ai_summary = "AI summary could not be generated: " + str(e)
                    
                st.markdown("### AI Insight")
                st.write(ai_summary)
                print(ai_summary)
                # KPI Cards, Chart, etc. (your existing code)
                avg_risk = driver_df["risk_score"].mean()
                max_speed = driver_df["speed"].max()
                avg_stress = (
                    driver_df["stress_level"].mean()
                    if driver_df["stress_level"].dtype != "O"
                    else None
                )

                col1, col2, col3 = st.columns(3)
                col1.metric("Average Risk Score", f"{avg_risk:.2f}")
                col2.metric("Top Speed (km/h)", f"{max_speed:.1f}")
                if avg_stress is not None:
                    col3.metric("Average Stress Level", f"{avg_stress:.2f}")
                else:
                    col3.metric("Stress Level", "N/A")
                driver_df["timestamp"] = pd.to_datetime(driver_df["timestamp"])
                driver_df = driver_df.sort_values(by="timestamp")
                st.markdown("### Risk Score Trend")
                fig = px.line(
                    driver_df,
                    x="timestamp",
                    y="risk_score",
                    color="driver_name",
                    markers=True,
                    title=f"Risk Score Over Time for Policy {policy_input}",
                    labels={"timestamp": "Timestamp", "risk_score": "Risk Score"},
                    template="plotly_dark",
                )
                fig.update_traces(line=dict(width=3))
                fig.update_layout(
                    height=500,
                    hovermode="x unified",
                    title_x=0.5,
                    title_font=dict(size=22, color="#212122"),
                    paper_bgcolor="#d9dce3",
                    plot_bgcolor="#bec0c5",
                    font=dict(color="white"),
                )
                st.plotly_chart(fig, use_container_width=True)

                with st.expander("View Full Driver Metrics Data"):
                    st.dataframe(driver_df, use_container_width=True)


