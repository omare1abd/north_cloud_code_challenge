import logging
import boto3
import onnxruntime as rt
from src.config import AWS_REGION, DYNAMODB_TABLE_NAME, MODEL_FILE_NAME

# --- Configure Logging ---
# This sets up a basic logger that will print messages to the console.
# In AWS Lambda, these logs will automatically be sent to CloudWatch.
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- Initialize AWS Clients ---
try:
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    s3_client = boto3.client("s3", region_name=AWS_REGION)
    table = dynamodb.Table(DYNAMODB_TABLE_NAME)
    logging.info("Successfully initialized AWS clients.")
except Exception as e:
    logging.error(f"Error initializing AWS clients: {e}", exc_info=True)
    table = None
    s3_client = None

# --- Load the ONNX Model ---
try:
    sess = rt.InferenceSession(MODEL_FILE_NAME)
    input_name = sess.get_inputs()[0].name
    label_name = sess.get_outputs()[0].name
    logging.info(f"Successfully loaded ONNX model: {MODEL_FILE_NAME}")
except FileNotFoundError:
    logging.error(f"Model file not found at '{MODEL_FILE_NAME}'")
    sess = None
except Exception as e:
    logging.error(f"Error loading ONNX model: {e}", exc_info=True)
    sess = None
