import boto3
import onnxruntime as rt
from src.config import AWS_REGION, DYNAMODB_TABLE_NAME, MODEL_FILE_NAME

# --- Initialize AWS Clients ---
try:
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    s3_client = boto3.client("s3", region_name=AWS_REGION)
    table = dynamodb.Table(DYNAMODB_TABLE_NAME)
    print("Successfully initialized AWS clients.")
except Exception as e:
    print(f"Error initializing AWS clients: {e}")
    table = None
    s3_client = None

# --- Load the ONNX Model ---
try:
    sess = rt.InferenceSession(MODEL_FILE_NAME)
    input_name = sess.get_inputs()[0].name
    label_name = sess.get_outputs()[0].name
    print(f"Successfully loaded ONNX model: {MODEL_FILE_NAME}")
except FileNotFoundError:
    print(f"Error: Model file not found at '{MODEL_FILE_NAME}'")
    sess = None
except Exception as e:
    print(f"Error loading ONNX model: {e}")
    sess = None
