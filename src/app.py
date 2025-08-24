import os
import json
import logging
from datetime import datetime
from boto3.dynamodb.conditions import Key

# Import agent and other components
from src.agent import Agent
from src.services import table, s3_client, sess
from src.config import RUNNING_LOCALLY, LOCAL_CSV_FILE_NAME
from src.utils import DecimalEncoder

# Configure logger
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def get_alerts(event):
    """Handles the GET /alerts API request, fetching all results at once."""
    logging.info("API request received for GET /alerts to fetch all items.")
    try:
        query_params = event.get("queryStringParameters") or {}

        if "source_file" not in query_params:
            logging.warning("API request missing 'source_file' query parameter.")
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {"error": "The 'source_file' query parameter is required."}
                ),
            }

        source_file = query_params["source_file"]
        pk_to_query = f"SOURCEFILE#{source_file}"
        logging.info(f"Querying DynamoDB for all alerts with PK: {pk_to_query}")

        all_items = []
        query_kwargs = {
            "KeyConditionExpression": Key("PK").eq(pk_to_query),
        }

        # Loop until all pages are fetched
        while True:
            response = table.query(**query_kwargs)
            all_items.extend(response.get("Items", []))

            # Check if there are more items to fetch
            last_evaluated_key = response.get("LastEvaluatedKey")
            if not last_evaluated_key:
                break  # Exit the loop if this is the last page

            # Set the starting point for the next page
            query_kwargs["ExclusiveStartKey"] = last_evaluated_key

        logging.info(
            f"Found a total of {len(all_items)} items for the given source file."
        )

        # Process all fetched items
        alerts = []
        for item in all_items:
            try:
                dt_object = datetime.strptime(item["Timestamp"], "%Y-%m-%d %H:%M:%S")
                iso_timestamp = dt_object.isoformat() + "Z"
            except (KeyError, ValueError):
                iso_timestamp = None
                logging.warning(f"Could not parse timestamp for item: {item.get('SK')}")

            alerts.append(
                {
                    "record_id": item.get("SourceFile", "unknown-source"),
                    "stress_score": int(item.get("OriginalStressLevel", 0)),
                    "timestamp": iso_timestamp,
                }
            )

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"alerts": alerts}, cls=DecimalEncoder),
        }
    except Exception as e:
        logging.error("Error processing GET /alerts request.", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Could not retrieve alerts."}),
        }


def handle_sqs_event(event):
    """Handles the SQS event trigger from S3 by using the Agent."""
    logging.info(f"Received {len(event.get('Records', []))} SQS records to process.")
    for record in event.get("Records", []):
        try:
            s3_event_str = record.get("body", "{}")
            s3_event = json.loads(s3_event_str)
            for s3_record in s3_event.get("Records", []):
                s3_bucket = s3_record["s3"]["bucket"]["name"]
                s3_key = s3_record["s3"]["object"]["key"]

                download_path = f"/tmp/{os.path.basename(s3_key)}"
                logging.info(
                    f"Downloading s3://{s3_bucket}/{s3_key} to {download_path}"
                )
                s3_client.download_file(s3_bucket, s3_key, download_path)

                # Instantiate and run the agent for the downloaded file
                agent = Agent()
                agent.run(file_path=download_path)

        except Exception as e:
            logging.error(
                f"Error processing SQS record: {record.get('messageId')}", exc_info=True
            )
            continue


def lambda_handler(event, context):
    """Main Lambda function handler."""
    logging.info("Lambda handler invoked.")

    if not all([table, s3_client, sess]):
        logging.critical(
            "A required client (DynamoDB, S3, or ONNX) failed to initialize. Aborting."
        )
        return {
            "statusCode": 500,
            "body": "A required client (DynamoDB, S3, or ONNX) failed to initialize.",
        }

    # API Gateway event
    if "httpMethod" in event:
        logging.info("Detected API Gateway event.")
        if event.get("path") == "/alerts" and event.get("httpMethod") == "GET":
            return get_alerts(event)
        else:
            logging.warning(
                f"Received unhandled API Gateway request: {event.get('httpMethod')} {event.get('path')}"
            )
            return {"statusCode": 404, "body": json.dumps({"error": "Not Found"})}

    # SQS event
    if (
        "Records" in event
        and "eventSource" in event["Records"][0]
        and event["Records"][0]["eventSource"] == "aws:sqs"
    ):
        logging.info("Detected SQS event.")
        handle_sqs_event(event)
        return {"statusCode": 200, "body": "Processing complete."}

    # Local execution
    if RUNNING_LOCALLY:
        logging.info("Detected local execution environment.")
        # Instantiate and run the agent for the local file
        agent = Agent()
        agent.run(file_path=LOCAL_CSV_FILE_NAME)
        return {"statusCode": 200, "body": "Local processing complete."}

    logging.warning("Handler received an unroutable event.", extra={"event": event})
    return {"statusCode": 400, "body": "Unrecognized event source."}
