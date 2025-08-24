import os

# --- DynamoDB Configuration ---
DYNAMODB_TABLE_NAME = "HighStressUsers"

# --- AWS Configuration ---
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

# --- Model Configuration ---
MODEL_FILE_NAME = "resources/stress_model.onnx"
STRESS_THRESHOLD = 42  # Updated to match the new model's training

# --- Local Development Configuration ---
# This is checked to determine if the Lambda is running locally
RUNNING_LOCALLY = os.environ.get("RUNNING_LOCALLY", "False")
LOCAL_CSV_FILE_NAME = "resources/university_mental_health_iot_dataset.csv"

# --- Feature Engineering Configuration ---
NUMERICAL_FEATURES = [
    "temperature_celsius",
    "humidity_percent",
    "air_quality_index",
    "noise_level_db",
    "lighting_lux",
    "crowd_density",
    "sleep_hours",
    "mood_score",
]
TRAINING_COLUMNS = NUMERICAL_FEATURES + [
    "location_id_101",
    "location_id_102",
    "location_id_103",
    "location_id_104",
    "location_id_105",
]
