import os
import uuid
import logging
from decimal import Decimal
import pandas as pd
import numpy as np

# Import shared services and configuration
from src.services import table, sess, input_name, label_name
from src.config import (
    STRESS_THRESHOLD,
    NUMERICAL_FEATURES,
    TRAINING_COLUMNS,
    RUNNING_LOCALLY,
)

# Configure logger
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def load_and_filter_data(file_path):
    """Loads data from a CSV and filters for potential high-stress records."""
    try:
        logging.info(f"Attempting to load data from {file_path}.")
        df = pd.read_csv(file_path, parse_dates=["timestamp"])
        logging.info(f"Successfully loaded {len(df)} rows from {file_path}.")

        # Pre-filter for users who meet the stress threshold
        potential_high_stress_df = df[df["stress_level"] > STRESS_THRESHOLD].copy()
        logging.info(
            f"Found {len(potential_high_stress_df)} records exceeding stress threshold of {STRESS_THRESHOLD}."
        )
        return potential_high_stress_df
    except Exception as e:
        logging.error(
            f"Failed to read or filter CSV file at {file_path}: {e}", exc_info=True
        )
        return None


def run_inference(dataframe):
    """Runs model inference on the provided dataframe."""
    predictions = []
    logging.info(f"Starting model inference for {len(dataframe)} records.")
    for index, row in dataframe.iterrows():
        try:
            # Prepare a single row for the model
            single_row_df = pd.DataFrame([row])
            location_dummies = pd.get_dummies(
                single_row_df["location_id"], prefix="location_id", dtype=float
            )
            processed_row = pd.concat(
                [single_row_df[NUMERICAL_FEATURES], location_dummies], axis=1
            )
            final_input = processed_row.reindex(columns=TRAINING_COLUMNS, fill_value=0)
            model_input = final_input.to_numpy().astype(np.float32)

            # Run inference
            prediction_result = sess.run([label_name], {input_name: model_input})[0][0]

            if prediction_result == 1:
                predictions.append(row.to_dict())
        except Exception as e:
            logging.error(f"Error during inference for row {index}: {e}", exc_info=True)
            continue
    logging.info(
        f"Inference complete. Found {len(predictions)} high-stress predictions."
    )
    return predictions


def store_predictions(predictions, source_file_path):
    """Stores the given predictions in DynamoDB."""
    items_inserted = 0
    source_filename = os.path.basename(source_file_path)
    logging.info(f"Attempting to store {len(predictions)} predictions in DynamoDB.")

    for row in predictions:
        try:
            user_id = str(uuid.uuid4())
            # Pandas may convert timestamp back to a Timestamp object
            timestamp_obj = pd.to_datetime(row["timestamp"])
            timestamp_str = timestamp_obj.strftime("%Y-%m-%d %H:%M:%S")

            pk = f"SOURCEFILE#{source_filename}"
            sk = f"LOCATION#{row['location_id']}#USERID#{user_id}"

            item = {
                "PK": pk,
                "SK": sk,
                "UserID": user_id,
                "Timestamp": timestamp_str,
                "SourceFile": source_filename,
                "LocationID": int(row["location_id"]),
                "OriginalStressLevel": Decimal(str(row["stress_level"])),
                "PredictedStressLabel": 1,
                "SleepHours": Decimal(str(row["sleep_hours"])),
                "MoodScore": Decimal(str(row["mood_score"])),
                "NoiseLevelDB": Decimal(str(row["noise_level_db"])),
            }

            if not RUNNING_LOCALLY:
                table.put_item(Item=item)
            items_inserted += 1
        except Exception as e:
            logging.error(
                f"Failed to store prediction for user {row.get('UserID', 'N/A')}: {e}",
                exc_info=True,
            )
            continue

    logging.info(f"Successfully inserted {items_inserted} records into DynamoDB.")
    return items_inserted
