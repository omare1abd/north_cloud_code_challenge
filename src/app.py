import os
import json
from datetime import datetime
from boto3.dynamodb.conditions import Key

# Import shared services, config, and utilities
from src.services import table, s3_client, sess
from src.config import LOCAL_CSV_FILE_NAME
from src.utils import DecimalEncoder
from src.processing import process_csv_file

def get_alerts(event):
    """Handles the GET /alerts API request."""
    try:
        query_params = event.get("queryStringParameters")

        if not query_params or "source_file" not in query_params:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "The 'source_file' query parameter is required."})
            }

        source_file = query_params["source_file"]
        pk_to_query = f"SOURCEFILE#{source_file}"
        print(f"Querying for alerts with PK: {pk_to_query}")

        response = table.query(KeyConditionExpression=Key('PK').eq(pk_to_query))
        items = response.get("Items", [])
        
        alerts = []
        for item in items:
            try:
                dt_object = datetime.strptime(item["Timestamp"], "%Y-%m-%d %H:%M:%S")
                iso_timestamp = dt_object.isoformat() + "Z"
            except (KeyError, ValueError):
                iso_timestamp = None
            
            alerts.append({
                "record_id": item.get("SourceFile", "unknown-source"),
                "stress_score": int(item.get("OriginalStressLevel", 0)),
                "timestamp": iso_timestamp,
            })
            
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(alerts, cls=DecimalEncoder),
        }
    except Exception as e:
        print(f"Error querying and transforming DynamoDB data: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Could not retrieve alerts."}),
        }

def handle_sqs_event(event):
    """Handles the SQS event trigger from S3."""
    print("--- Running in Cloud Mode (Polling SQS) ---")
    for record in event.get("Records", []):
        try:
            s3_event_str = record.get("body", "{}")
            s3_event = json.loads(s3_event_str)
            for s3_record in s3_event.get("Records", []):
                s3_bucket = s3_record["s3"]["bucket"]["name"]
                s3_key = s3_record["s3"]["object"]["key"]
                
                download_path = f"/tmp/{os.path.basename(s3_key)}"
                print(f"Downloading s3://{s3_bucket}/{s3_key} to {download_path}")
                s3_client.download_file(s3_bucket, s3_key, download_path)
                
                process_csv_file(download_path)
        except Exception as e:
            print(f"Error processing SQS record: {e}")
            continue

def lambda_handler(event, context):
    """Main Lambda function handler."""
    if not all([table, s3_client, sess]):
        return {
            "statusCode": 500,
            "body": "A required client (DynamoDB, S3, or ONNX) failed to initialize.",
        }

    # API Gateway event
    if "httpMethod" in event:
        print("--- Running in API Gateway Mode ---")
        if event.get("path") == "/alerts" and event.get("httpMethod") == "GET":
            return get_alerts(event)
        else:
            return {"statusCode": 404, "body": json.dumps({"error": "Not Found"})}

    # SQS event
    if "Records" in event and "eventSource" in event["Records"][0] and event["Records"][0]["eventSource"] == "aws:sqs":
        handle_sqs_event(event)
        return {"statusCode": 200, "body": "Processing complete."}

    # Local execution
    if os.environ["RUNNING_LOCALLY"] == "True":
        print("--- Running in Local Mode ---")
        process_csv_file(LOCAL_CSV_FILE_NAME)
        return {"statusCode": 200, "body": "Local processing complete."}

    print("Handler received unroutable event:", event)
    return {"statusCode": 400, "body": "Unrecognized event source."}

