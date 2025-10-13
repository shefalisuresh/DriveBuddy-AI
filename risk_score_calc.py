import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.ensemble import RandomForestRegressor

def generate_csv():
    # -----------------------------
    # Load telemetry CSV
    # -----------------------------
    telemetry_df = pd.read_csv("telemetry_smart_gadget_alice.csv")
    
    # -----------------------------
    # Thresholds for event detection
    # -----------------------------
    HARSH_BRAKE_THRESHOLD = 0.7     # braking value >0.7 → harsh braking
    OVERSPEED_THRESHOLD = 100       # km/h → overspeed
    SHARP_TURN_THRESHOLD = 5.0      # placeholder for angular velocity if available
    
    telemetry_df["event"] = None
    
    # Iterate through rows to detect events
    for idx, row in telemetry_df.iterrows():
        events = []  # list to store multiple events if needed
        
        if row["braking"] > HARSH_BRAKE_THRESHOLD:
            events.append("harsh_brake")
    
        if row["speed"] > OVERSPEED_THRESHOLD:
            events.append("overspeed")
    
        # Example: if you have angular velocity data
        if "angular_velocity" in telemetry_df.columns and row["angular_velocity"] > SHARP_TURN_THRESHOLD:
            events.append("sharp_turn")
    
        # Join events (comma separated if multiple triggered)
        telemetry_df.at[idx, "event"] = ", ".join(events) if events else "normal"
    # -----------------------------
    # Simulated traffic data (for demonstration)
    # -----------------------------
    np.random.seed(42)
    traffic_levels = ['low', 'medium', 'high']
    traffic_df = telemetry_df[['timestamp','vehicle_id']].copy()
    traffic_df['traffic_density'] = np.random.choice(traffic_levels, size=len(traffic_df))
    
    # -----------------------------
    # Merge telemetry + traffic
    # -----------------------------
    df = telemetry_df.merge(traffic_df, on=['timestamp','vehicle_id'])
    
    # -----------------------------
    # Encode categorical features
    # -----------------------------
    weather_map = {'Clear':0, 'Rain':1, 'Fog':2}
    road_map = {'highway':0, 'city':1, 'rural':2}
    traffic_map = {'low':0, 'medium':1, 'high':2}
    
    df['weather_encoded'] = df['weather'].map(weather_map)
    df['road_encoded'] = df['road_type'].map(road_map)
    df['traffic_encoded'] = df['traffic_density'].map(traffic_map)
    
    # -----------------------------
    # Select features for context fusion
    # -----------------------------
    features = ['speed','braking','acceleration','weather_encoded','road_encoded','traffic_encoded']
    
    X = df[features]
    
    # Normalize features
    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(X)
    
    # -----------------------------
    # Train a simple model (RandomForest) to compute a risk score
    # For demonstration, we generate a synthetic target
    # -----------------------------
    y = 0.5*X_scaled[:,0] + 0.3*X_scaled[:,1] + 0.2*X_scaled[:,5]  # speed*0.5 + braking*0.3 + traffic*0.2
    y = np.clip(y, 0, 1)  # risk score between 0 and 1
    
    model = RandomForestRegressor(n_estimators=50, random_state=42)
    model.fit(X_scaled, y)
    
    # -----------------------------
    # Predict risk scores (context fusion)
    # -----------------------------
    df['risk_score'] = model.predict(X_scaled)
    output_cols = [
        'timestamp', 'driver_name','policy_number', 'vehicle_id', 'gps_lat', 'gps_lon',
        'speed', 'braking', 'traffic_density','weather','road_type', 'stress_level','heart_rate','gsr','fatigue',"event", 'risk_score'
    ]
    output_df = df[output_cols]
    # Save results
    output_df.to_csv("fleet_context_fusion.csv", index=False)
    print("Context-fused risk scores saved to 'fleet_context_fusion.csv'")
    print(df[['timestamp','vehicle_id','speed','braking','traffic_density','risk_score']].head())
