import streamlit as st
import pandas as pd
from geopy.distance import geodesic
from groq import Groq
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
from gtts import gTTS
import tempfile
import os
import subprocess
from risk_score_calc import generate_csv

try:
    csv_file = generate_csv()  # runs inside the same Python environment
    st.success(f"CSV generated successfully: {csv_file}")
except Exception as e:
    st.error(f"Failed to generate CSV: {e}")
# ==============================
# --- Load Rest Area Data ---
# ==============================
@st.cache_data
def load_rest_areas():
    rest_area_json = "https://data.ny.gov/resource/qebf-4fd8.json"
    rest_df = pd.read_json(rest_area_json)
    rest_df = rest_df[['name', 'description', 'travel_direction', 'latitude', 'longitude']]
    return rest_df

rest_df = load_rest_areas()

def nearest_rest_area(lat, lon):
    nearest = None
    min_dist = float('inf')
    for _, row in rest_df.iterrows():
        dist = geodesic((lat, lon), (row['latitude'], row['longitude'])).kilometers
        if dist < min_dist:
            min_dist = dist
            nearest = row
    return nearest

# ==============================
# --- Few-shot Prompt Examples ---
# ==============================
few_shot_examples = [
    {
        "prompt": "Vehicle ID: V1\nRisk Score: 0.61\nWeather: Overcast\nRoad Type: highway\nTraffic Density: high\nGenerate a short, friendly, motivational driving nudge:",
        "completion": "Vehicle V1: 🚗 Moderate risk. Keep an eye on traffic and adjust speed for safer driving."
    },
    {
        "prompt": "Vehicle ID: V2\nRisk Score: 0.85\nWeather: Rain\nRoad Type: city\nTraffic Density: medium\nGenerate a short, friendly, motivational driving nudge:",
        "completion": "Vehicle V2: ⚠️ High risk detected! Drive very carefully in rainy city conditions."
    },
    {
        "prompt": "Vehicle ID: V3\nRisk Score: 0.35\nWeather: Clear\nRoad Type: highway\nTraffic Density: low\nGenerate a short, friendly, motivational driving nudge:",
        "completion": "Vehicle V3: ✅ Low risk. Great driving! Keep up the safe habits."
    }
]

def build_few_shot_text(examples):
    return "\n\n".join(
        f"Example:\n{e['prompt']}\nResponse: {e['completion']}"
        for e in examples
    )

FEW_SHOT_TEXT = build_few_shot_text(few_shot_examples)

# ==============================
# --- Groq AI Generation ---
# ==============================
def generate_nudge_via_groq(
    groq_client: Groq,
    timestamp, driver_name, vehicle_id, gps_lat, gps_lon,
    weather, road_type, risk_score, traffic_density,
    stress_level, heart_rate, gsr, fatigue,event
):
    rest_area = None
    if stress_level > 70:
        rest_area = nearest_rest_area(gps_lat, gps_lon)

    rest_text = ""
    if rest_area is not None:
        rest_text = (
            f"Suggested Rest Area: {rest_area['name']} ({rest_area['description']}) "
            f"at lat {rest_area['latitude']}, lon {rest_area['longitude']}\n"
        )

    prompt = f"""
You are a friendly AI driving assistant that provides motivational driving nudges. Use these examples for style and tone:

{FEW_SHOT_TEXT}

Now generate a new driving alert:

timestamp: {timestamp}
Driver Name: {driver_name}
Vehicle ID: {vehicle_id}
gps_lat: {gps_lat}
gps_lon: {gps_lon}
Weather: {weather}
Road Type: {road_type}
Risk Score: {risk_score:.2f}
Traffic Density: {traffic_density}
Stress Level: {stress_level}
Heart Rate: {heart_rate}
GSR: {gsr}
Fatigue: {fatigue}
Event: {event}
{rest_text}
Generate a short, friendly, alert driving nudge based on the actual stress level ({stress_level})
and actual risk score ({risk_score:.2f}). If the stress level is above 70 and risk_score > 0.8, clearly suggest the nearest rest area.
Driving Alert:
"""

    messages = [
        {"role": "system", "content": "You are a motivational driving assistant."},
        {"role": "user", "content": prompt}
    ]
    resp = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages,
        temperature=0.2
    )
    return resp.choices[0].message.content.strip()

# ==============================
# --- Streamlit App Setup ---
# ==============================
st.set_page_config(page_title="DriveBuddy 🚦", layout="wide")
st.title("🚦 DriveBuddy — Smart Driving Alert System")
st.markdown(
    """
    <div style="
        background-color:#f0f2f6;
        padding:12px 20px;
        border-radius:10px;
        border-left:5px solid #4b8bbe;
        margin-bottom:15px;
    ">
        <b>Disclaimer:</b> Prototype demonstrates AI-driven nudges. 
        Full solution will include bias checks, privacy safeguards, 
        and regulatory compliance.
    </div>
    """,
    unsafe_allow_html=True
)

# --- Styling ---
st.markdown("""
<style>
.dashboard-card {
    background-color: #ffffff;
    border-radius: 18px;
    padding: 25px;
    margin-bottom: 25px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.08);
}
.metric-label {
    font-weight: 600;
    color: #555;
}
.progress-container {
    background-color: #eee;
    border-radius: 10px;
    height: 10px;
    overflow: hidden;
    margin-top: 4px;
}
.progress-bar {
    height: 10px;
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

# --- Groq API ---
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- Load CSV data ---
try:
    df = pd.read_csv('fleet_context_fusion.csv')
    df = df[(df['risk_score'] >= 0.85) & (df['stress_level'] >= 65)]
except Exception as e:
    st.error(f"Could not load data file: {e}")
    st.stop()

if df.empty:
    st.warning("No data available in CSV.")
    st.stop()

st.write("🔍 Data loaded. Number of rows:", len(df))

# ==============================
# --- Auto Refresh + State ---
# ==============================
if "alert_idx" not in st.session_state:
    st.session_state.alert_idx = 0
if "finished" not in st.session_state:
    st.session_state.finished = False

# Only refresh if not finished
if not st.session_state.finished:
    refresh_count = st_autorefresh(interval=30000, key="auto_alert_refresh")
else:
    refresh_count = 0

# Increment index on refresh
if refresh_count > 0 and not st.session_state.finished:
    if st.session_state.alert_idx < len(df) - 1:
        st.session_state.alert_idx += 1
    else:
        st.session_state.finished = True

# ==============================
# --- Display Section ---
# ==============================
if not st.session_state.finished:
    idx = st.session_state.alert_idx
    row = df.iloc[idx]

    # --- Extract fields ---
    timestamp = row.get("timestamp", datetime.now().isoformat())
    driver_name = row.get("driver_name", "Unknown")
    vehicle_id = row.get("vehicle_id", "Unknown")
    gps_lat = float(row.get("gps_lat", 0.0))
    gps_lon = float(row.get("gps_lon", 0.0))
    weather = row.get("weather", "Unknown")
    road_type = row.get("road_type", "Unknown")
    risk_score = float(row.get("risk_score", 0.0))
    traffic_density = row.get("traffic_density", "Unknown")
    stress_level = float(row.get("stress_level", 0.0))
    heart_rate = float(row.get("heart_rate", 0.0))
    gsr = float(row.get("gsr", 0.0))
    fatigue = float(row.get("fatigue", 0.0))
    event = row.get("event", "Unknown")
    # --- Fancy Card ---
    st.markdown(f"## 🕒 Data Snapshot — `{timestamp}` (Row {idx+1}/{len(df)})")
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("👤 Driver", driver_name)
    with col2:
        st.metric("🚘 Vehicle", vehicle_id)
    with col3:
        st.metric("🛣️ Road Type", road_type)

    st.markdown("---")

    col4, col5, col6 = st.columns(3)
    with col4:
        st.metric("🌤 Weather", weather)
    with col5:
        st.metric("🚦 Traffic", traffic_density)
    with col6:
        st.metric("⚡ Risk Score", f"{risk_score:.2f}")
    # --- Handle event(s) from data ---
    # If your row has a column named 'event'
    # --- Extract and parse event(s) ---
    event_data = row.get("event", "normal")

    # Ensure it's a list of event strings
    if isinstance(event_data, str):
        events = [e.strip() for e in event_data.split(",") if e.strip()]
    else:
        events = ["normal"]

    # --- Define color map for events ---
    color_map = {
        "overspeed": "#e74c3c",       # red
        "harsh_brake": "#f39c12",     # orange
        "sharp_turn": "#9b59b6",      # purple
        "fatigue": "#8e44ad",         # violet
        "high_stress": "#d35400",     # deep orange
        "normal": "#2ecc71"           # green
    }

    # --- Generate fancy event badges ---
    badges_html = ""
    for ev in events:
        color = color_map.get(ev.lower(), "#95a5a6")
        badges_html += f'<span style="background-color:{color}; color:white; padding:6px 12px; border-radius:20px; margin-right:6px; font-weight:600; display:inline-block; box-shadow:0 3px 6px rgba(0,0,0,0.1);">{ev.upper()}</span>'
    # --- Display event badges ---
    st.markdown(f"""
    <div style="
        margin-top:10px;
        text-align:center;
    ">
    🚘 <b>Event(s) Detected:</b><br>
    {badges_html}
    </div>
    """, unsafe_allow_html=True)

    # --- Progress bar helper ---
    def progress_bar_html(value, color):
        pct = min(max(value, 0), 100)
        return f"""
        <div class='progress-container'>
            <div class='progress-bar' style='width:{pct}%; background-color:{color};'></div>
        </div>
        """

    st.markdown("### 📊 Driver Condition")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"**😰 Stress Level: {stress_level:.0f}**")
        st.markdown(progress_bar_html(stress_level, "#e74c3c" if stress_level > 70 else "#f1c40f"), unsafe_allow_html=True)
    with c2:
        st.markdown(f"**💓 Heart Rate: {heart_rate:.0f} bpm**")
        st.markdown(progress_bar_html(min(heart_rate / 2, 100), "#3498db"), unsafe_allow_html=True)
    with c3:
        st.markdown(f"**😴 Fatigue: {fatigue:.0f}**")
        st.markdown(progress_bar_html(fatigue, "#9b59b6"), unsafe_allow_html=True)

    st.markdown("---")
    st.map(pd.DataFrame([{"lat": gps_lat, "lon": gps_lon}]))
    st.markdown('</div>', unsafe_allow_html=True)

    # --- Alert Status ---
    if risk_score > 0.8 and stress_level > 70:
        st.error("🚨 Critical Condition — High risk and high stress! Recommend immediate rest.")
        st.audio("assets/critical.mp4",autoplay=True)  # Local file
    elif risk_score > 0.6:
        st.warning("⚠️ Elevated risk detected — stay cautious.")
        st.audio("assets/warning.mp3",autoplay=True)
    elif stress_level > 70:
        st.warning("😟 High stress level — consider a short break.")
        st.audio("assets/warning.mp3",autoplay=True)
    else:
        st.success("✅ Safe driving conditions — keep it steady!")

    # --- AI Nudge ---
    alert = generate_nudge_via_groq(
        client, timestamp, driver_name, vehicle_id,
        gps_lat, gps_lon, weather, road_type,
        risk_score, traffic_density, stress_level, heart_rate, gsr, fatigue,event
    )
    st.markdown("### 💬 AI Driving Nudge")
    st.info(f"**{alert}**")

# --- Text-to-Speech (TTS) ---
    def speak_text(text):
        """Generate and play AI nudge audio using Google TTS."""
        if not text:
            st.warning("No text to speak.")
            return

        # Generate audio using gTTS
        tts = gTTS(text=text, lang='en', slow=False)

        # Save to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            tts.save(tmp_file.name)
            st.audio(tmp_file.name, format="audio/mp3", start_time=0)

    # Add a "🎙️ Speak Nudge" button
    speak_text(alert)

    # --- Rest Area Suggestion with Directions ---
    if stress_level > 70:
        rest = nearest_rest_area(gps_lat, gps_lon)
        if rest is not None:
            st.markdown("### 🛑 Suggested Rest Area")
            st.info(f"**{rest['name']}** — {rest['description']}")

            rest_lat, rest_lon = rest["latitude"], rest["longitude"]

            # --- Static Google Maps Route ---
            google_static_map_url = (
                f"https://maps.googleapis.com/maps/api/staticmap?"
                f"size=600x400&path=color:0x0000ff|weight:4|{gps_lat},{gps_lon}|{rest_lat},{rest_lon}"
                f"&markers=color:green|label:S|{gps_lat},{gps_lon}"
                f"&markers=color:red|label:R|{rest_lat},{rest_lon}"
            )

            # Display static map
            st.image(google_static_map_url, caption="Route to Nearest Rest Area", use_container_width=True)

            # --- Clickable Live Directions ---
            maps_directions_url = (
                f"https://www.google.com/maps/dir/?api=1"
                f"&origin={gps_lat},{gps_lon}"
                f"&destination={rest_lat},{rest_lon}"
                f"&travelmode=driving"
            )
            st.markdown(f"[🗺️ Open Directions in Google Maps]({maps_directions_url})", unsafe_allow_html=True)


            # Optionally, add a short delay between showing next alert
        # time.sleep(2)  # 2 seconds — you can adjust or remove this

else:
    st.success("✅ All alerts have been shown.")
    st.markdown("## 🧠 AI Driving Summary")

    # Build a text summary from the dataset
    summary_prompt = f"""
You are an AI driving coach. Analyze this driving dataset summary:

Total Records: {len(df)}
Average Risk Score: {df['risk_score'].mean():.2f}
Average Stress Level: {df['stress_level'].mean():.2f}
Average Fatigue: {df['fatigue'].mean():.2f}
Traffic Densities: {df['traffic_density'].value_counts().to_dict()}
Weather Conditions: {df['weather'].value_counts().to_dict()}

Based on these patterns, write a short, friendly, motivational driving summary (max 150 words). 
Highlight general performance, safety behavior, and personalized encouragement. 
Use an uplifting tone and emojis where appropriate.
    """

    try:
        summary_resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a motivational driving coach."},
                {"role": "user", "content": summary_prompt}
            ],
            temperature=0.4
        )

        summary_text = summary_resp.choices[0].message.content.strip()
        st.info(summary_text)

    except Exception as e:
        st.warning(f"Could not generate AI summary: {e}")
        

