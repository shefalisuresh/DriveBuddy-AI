# Fleet Risk Intelligence Prototype 🚗💡

This project demonstrates an **AI-driven fleet risk assessment system** that combines **driver telemetry**, **context fusion**, and **LLM-based validation** to produce explainable risk scores for vehicle insurance and driver safety insights.

---

## ⚙️ Overview

The system integrates:
- **Telemetry data** (speed, braking, acceleration, fatigue, etc.)
- **Contextual information** (weather, road type, traffic)
- **Machine Learning (Random Forest)** for computing risk scores
- **LLM-as-a-Judge** to validate consistency and explain results
- **Streamlit UI** for visualization and ethical transparency

---

## 🧩 Key Features

✅ **Context Fusion:**  
Combines environmental and driver factors into a single risk score.

✅ **Event Detection:**  
Detects events like harsh braking, overspeeding, and sharp turns from raw telemetry.

✅ **Risk Scoring Model:**  
Uses a trained Random Forest regressor to estimate per-driver risk probability (0–1 scale).

✅ **Validation Engine (LLM as Judge):**  
Cross-validates computed risk scores against raw data and logs inconsistencies for further analysis.

✅ **Ethical & Responsible AI:**  
Includes explainability, fairness monitoring, and a built-in disclaimer to ensure responsible model use.

---

## 🧰 Tech Stack

| Component | Technology |
|------------|-------------|
| Data Processing | Python, Pandas, NumPy |
| ML Model | Scikit-learn (RandomForestRegressor) |
| Normalization | MinMaxScaler |
| UI | Streamlit |
| Validation | LLM (Groq Llama 3.1 8B Instant) |
| Logging | JSON structured logs |
| Data Sources | Telematics CSV (e.g., `telemetry_smart_gadget_alice.csv`) |

---

## 🚀 How to Run

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/<your-username>/fleet-risk-ai.git
   cd fleet-risk-ai
   ```
2. **Run the Streamlit App**
   ```bash
   streamlit run app.py
   ```
**Output Files**

- `fleet_context_fusion.csv` → Contains risk scores with contextual fusion
- `validation_log.json` → Logs LLM judge verdicts and mismatches

⚖️ Ethical AI & Responsible Use

This prototype ensures:
- Transparency: Risk factors are interpretable.
- Fairness: Biases in training data are identified for future mitigation.
- Privacy: Sensitive data is anonymized before analysis.
- Accountability: LLM validation ensures traceable, explainable results.
