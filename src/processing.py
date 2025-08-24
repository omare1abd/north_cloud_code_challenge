import os
import uuid
from decimal import Decimal
import pandas as pd
import numpy as np

# Import shared services and configuration
from src.services import table, sess, input_name, label_name
from src.config import (
    STRESS_THRESHOLD,
    NUMERICAL_FEATURES,
    TRAINING_COLUMNS,
    RUNNING_LOCALLY
)

def process_csv_file(file_path):
    """
    Core logic to process a single CSV file for high-stress users.
    """
    try:
        df = pd.read_csv(file_path, parse_dates=["timestamp"])
        print(f"Successfully loaded CSV data with {len(df)} rows from {file_path}.")
    except Exception as e:
        print(f"Error reading CSV file at {file_path}: {e}")
        return

    source_filename = os.path.basename(file_path)

    # Pre-filter for users who meet the stress threshold
    potential_high_stress_df = df[df["stress_level"] > STRESS_THRESHOLD].copy()
    potential_count = len(potential_high_stress_df)
    print(
        f"Found {potential_count} users with stress_level > {STRESS_THRESHOLD}. Now running model validation."
    )
    if potential_count == 0:
        return

    items_inserted = 0
    for index, row in potential_high_stress_df.iterrows():
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
            prediction = sess.run([label_name], {input_name: model_input})[0][0]

            # Write to DynamoDB if high stress is predicted
            if prediction == 1:
                user_id = str(uuid.uuid4())
                timestamp_str = row["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
                
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
                    "PredictedStressLabel": int(prediction),
                    "SleepHours": Decimal(str(row["sleep_hours"])),
                    "MoodScore": Decimal(str(row["mood_score"])),
                    "NoiseLevelDB": Decimal(str(row["noise_level_db"])),
                }
                
                if not RUNNING_LOCALLY:
                    table.put_item(Item=item)
                items_inserted += 1
        except Exception as e:
            print(f"Error processing row {index}: {e}")
            continue
            
    print(
        f"Successfully processed {items_inserted} records from {file_path}."
    )
