from src.app import lambda_handler
import os

os.environ["RUNNING_LOCALLY"] = "True"
# --- Example of how to run this locally (for testing) ---
if __name__ == "__main__":
    # This block will only run when you execute the script directly
    # It will not run in the AWS Lambda environment
    print("--- Running script locally for testing ---")

    # You need to have AWS credentials configured for this to work
    # (e.g., via `aws configure` or environment variables)
    # Also, ensure the DynamoDB table 'HighStressUsers' with primary key 'UserID' exists.

    # Mock the event and context objects that Lambda provides
    mock_event = {}
    mock_context = {}

    response = lambda_handler(mock_event, mock_context)
    print("\n--- Lambda handler response ---")
    print(response)
