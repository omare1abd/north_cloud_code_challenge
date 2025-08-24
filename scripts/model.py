import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score, classification_report
import joblib
import numpy as np

# ONNX-related imports
try:
    import onnxruntime as rt
    from skl2onnx import convert_sklearn
    from skl2onnx.common.data_types import FloatTensorType

    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    print(
        "Warning: 'skl2onnx' or 'onnxruntime' not found. ONNX conversion will be skipped."
    )
    print("Install them with: pip install skl2onnx onnxruntime")


# --- 1. Load and Prepare the Data ---
# Load the dataset provided for the project.
try:
    df = pd.read_csv("university_mental_health_iot_dataset.csv")
except FileNotFoundError:
    print(
        "Error: Make sure 'university_mental_health_iot_dataset.csv' is in the same directory."
    )
    exit()

# Define the stress threshold from the project requirements.
STRESS_THRESHOLD = 42  # Updated based on data analysis

# Create the target variable 'is_high_stress'.
# This is what the model will learn to predict.
# 1 means high stress, 0 means normal stress.
df["is_high_stress"] = (df["stress_level"] > STRESS_THRESHOLD).astype(int)

# --- 2. Feature Engineering ---
# We select a few relevant columns that might influence stress.
numerical_features = [
    "temperature_celsius",
    "humidity_percent",
    "air_quality_index",
    "noise_level_db",
    "lighting_lux",
    "crowd_density",
    "sleep_hours",
    "mood_score",
]

# One-hot encode the 'location_id' categorical feature
location_dummies = pd.get_dummies(df["location_id"], prefix="location_id", dtype=float)

# Combine numerical features with the new one-hot encoded location features
X = pd.concat([df[numerical_features], location_dummies], axis=1)
y = df["is_high_stress"]

# --- 3. Split Data for Training and Testing ---
# This is a standard ML practice to evaluate the model's performance.
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"Training data shape: {X_train.shape}")
print(f"Testing data shape: {X_test.shape}")

# --- 4. Train the Decision Tree Model ---
# We use a DecisionTreeClassifier.
# 'max_depth=5' keeps the model simple and "lightweight" to prevent overfitting.
print("\nTraining the Decision Tree model...")
model = DecisionTreeClassifier(max_depth=5, random_state=42)
model.fit(X_train, y_train)
print("Model training complete.")

# --- 5. Evaluate the Model's Performance ---
print("\nEvaluating model performance...")
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
print(f"Model Accuracy: {accuracy:.4f}")
print("\nClassification Report:")
print(
    classification_report(y_test, y_pred, target_names=["Normal Stress", "High Stress"])
)

# --- 6. Save the Trained Model (Joblib format) ---
# We save the model using joblib for general Python use.
model_filename = "stress_model.joblib"
joblib.dump(model, model_filename)
print(f"\nModel successfully saved to '{model_filename}'")

# --- 7. Convert and Save the Model to ONNX format ---
if ONNX_AVAILABLE:
    print("\nConverting model to ONNX format...")
    # Define the input type for the ONNX model.
    # We expect a float tensor of shape [batch_size, num_features].
    initial_type = [("float_input", FloatTensorType([None, X_train.shape[1]]))]

    # Convert the scikit-learn model to ONNX.
    onnx_model = convert_sklearn(model, initial_types=initial_type, target_opset=12)

    # Save the ONNX model to a file.
    onnx_filename = "stress_model.onnx"
    with open(onnx_filename, "wb") as f:
        f.write(onnx_model.SerializeToString())
    print(f"Model successfully converted and saved to '{onnx_filename}'")


# --- 8. Example of How to Use the Models (This part goes in your Lambda) ---
print("\n--- Example Predictions for a New Student ---")

# Simulate new data for a single student (as if it came from the uploaded CSV)
new_student_data = {
    "temperature_celsius": [25.5],
    "humidity_percent": [60.1],
    "air_quality_index": [80],
    "noise_level_db": [65.2],
    "lighting_lux": [450],
    "crowd_density": [25],
    "sleep_hours": [4.5],  # Low sleep
    "mood_score": [1.2],  # Low mood
    "location_id": [103],  # Example location
}
new_student_df = pd.DataFrame(new_student_data)

# IMPORTANT: Apply the same one-hot encoding to the new data
new_location_dummies = pd.get_dummies(
    new_student_df["location_id"], prefix="location_id", dtype=float
)
new_student_processed = pd.concat(
    [new_student_df[numerical_features], new_location_dummies], axis=1
)

# Align columns with the training data to ensure consistency
# This adds any missing location columns and fills them with 0
final_input = new_student_processed.reindex(columns=X_train.columns, fill_value=0)


# A) Using the joblib model
print("\n1. Prediction using joblib model:")
loaded_model = joblib.load(model_filename)
prediction = loaded_model.predict(final_input)
print(f"   Prediction: {'High Stress' if prediction[0] == 1 else 'Normal Stress'}")

# B) Using the ONNX model
if ONNX_AVAILABLE:
    print("\n2. Prediction using ONNX model:")
    # Create an ONNX runtime inference session
    sess = rt.InferenceSession(onnx_filename)
    input_name = sess.get_inputs()[0].name
    # The first output is the label, the second is the probabilities.
    label_name = sess.get_outputs()[0].name

    # Prepare the data as a numpy array of type float32.
    new_student_np = final_input.to_numpy().astype(np.float32)

    # Run inference. The result is a list containing the output arrays.
    result = sess.run([label_name], {input_name: new_student_np})
    prediction_onnx = result[0][0]

    print(
        f"   Prediction: {'High Stress' if prediction_onnx == 1 else 'Normal Stress'}"
    )
