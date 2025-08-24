# High-Stress User Detection Application

## Overview

This serverless application automatically processes IoT data from CSV files to identify and store records of individuals exhibiting high stress levels. It uses a pre-trained ONNX machine learning model to predict stress based on environmental and physiological factors.

The architecture is event-driven and built entirely on AWS services. It exposes a REST API endpoint to query the results for specific data files.

**Core Technologies:**

* **Backend**: Python 3.12
* **ML Model**: ONNX Runtime
* **Infrastructure**: AWS SAM, AWS Lambda, S3, SQS, DynamoDB, API Gateway

---

## Serverless Architecture

The application follows a classic event-driven pattern for processing and a serverless API for querying.

1.  **File Upload**: A user uploads a `.csv` file containing IoT sensor data to a designated **S3 Bucket**.
2.  **Notification**: The S3 bucket is configured to automatically send a notification message to an **SQS Queue** every time a new file is created.
3.  **Processing Trigger**: The **Lambda Function** is triggered by new messages appearing in the SQS queue. It processes one file at a time.
4.  **Data Processing**:
    * The Lambda function downloads the CSV file from S3.
    * It reads the data and uses a machine learning model to predict high-stress individuals.
    * Records identified as high-stress are written to a **DynamoDB Table** for persistent storage. The source filename is used as the partition key for efficient lookups.
5.  **API Query**:
    * An **API Gateway** endpoint (`GET /alerts`) is configured to trigger the same Lambda function.
    * When a request is made to this endpoint with a `source_file` query parameter, the function queries the DynamoDB table for all records associated with that file and returns them as a JSON response.

!(https://user-images.githubusercontent.com/1028328/130193131-43e61771-8b36-45a8-8a21-02a8385b0357.png)

---

## Prerequisites

Before deploying, ensure you have the following installed and configured:

* AWS CLI: [Installation Guide](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html)
* AWS SAM CLI: [Installation Guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
* Python 3.12
* Pipenv: [Installation Guide](https://pipenv.pypa.io/en/latest/installation/)
* Docker (required by SAM CLI for building deployment packages)

---

## Local Development and Testing

You can run the Lambda function on your local machine to test the core processing logic without deploying to AWS.

### 1. Installation

Clone the repository and install the required Python packages using the `Pipfile`.

```bash
git clone <your-repository-url>
cd <repository-directory>
pipenv install
```

### 2. Running Locally

Execute the `run_lambda_local.py` script within the Pipenv virtual environment. This script sets the `RUNNING_LOCALLY` environment variable and invokes the `lambda_handler`, which will process the local CSV file specified in `app.py`.

```bash
pipenv run local
```

---

## Deployment

The application is deployed as an AWS CloudFormation stack using the AWS SAM CLI.

1.  **Build the application**: This command packages your Lambda function code and dependencies into a format that can be deployed.
    ```bash
    sam build
    ```

2.  **Deploy the stack**: The `--guided` flag will prompt you for deployment parameters, such as the stack name, AWS region, and the names for your S3 bucket and DynamoDB table.
    ```bash
    sam deploy --guided
    ```
    Review the proposed changes and confirm the deployment. SAM will then provision all the AWS resources defined in the `template.yaml` file.

---

## Usage

After deployment, the SAM CLI will output the `ApiUrl` and `S3Bucket` name.

### 1. Processing a File

* Locate the `S3Bucket` name from the deployment output.
* Upload a CSV file (e.g., `university_mental_health_iot_dataset.csv`) to the root of this S3 bucket.
* This will automatically trigger the Lambda function, which will process the file and store any high-stress records in DynamoDB.

### 2. Querying Results via API

* Locate the `ApiUrl` from the deployment output.
* Make a `GET` request to this URL, ensuring you include the `source_file` query string parameter with the name of the file you uploaded.

**Example using `curl`**:

```bash
curl "https://<your-api-id>[.execute-api.us-east-1.amazonaws.com/Prod/alerts?source_file=university_mental_health_iot_dataset.csv](https://.execute-api.us-east-1.amazonaws.com/Prod/alerts?source_file=university_mental_health_iot_dataset.csv)"
```

**Example Response**:

```json
[
    {
        "record_id": "{file_name}{user_id}}",
        "stress_score": 45,
        "timestamp": "2024-01-15T10:00:00Z"
    },
    {
        "record_id": "{file_name}{user_id}",
        "stress_score": 52,
        "timestamp": "2024-01-15T10:05:00Z"
    }
]