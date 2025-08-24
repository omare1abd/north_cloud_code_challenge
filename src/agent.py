import time
import json
from src.processing import load_and_filter_data, run_inference, store_predictions


class Agent:
    """
    An agent that processes a CSV file to find and store high-stress user data.
    It follows a plan and logs its actions and observations.
    """

    def __init__(self):
        # The trace will store the log of actions for a single run
        self.trace = []

    def _log(self, message, data=None):
        """Adds a log entry to the agent's trace."""
        log_entry = {"timestamp": time.time(), "message": message, "data": data or {}}
        self.trace.append(log_entry)
        print(f"[AGENT LOG] {message}")

    def run(self, file_path):
        """
        Executes the agent's main loop to process a file.
        """
        self._log("Agent run started.", {"file_path": file_path})

        try:
            # --- Action 1: Load and Filter Data ---
            self._log("Initiating action: Load and filter data.")
            filtered_df = load_and_filter_data(file_path)

            if filtered_df is None:
                self._log("Observation: Data loading failed. Halting run.")
                return

            if filtered_df.empty:
                self._log(
                    "Observation: No potential high-stress users found after filtering. Halting run."
                )
                return

            self._log(
                "Observation: Data loaded and filtered successfully.",
                {"potential_records": len(filtered_df)},
            )

            # --- Action 2: Run Model Inference ---
            self._log("Initiating action: Run model inference.")
            predictions_to_store = run_inference(filtered_df)
            self._log(
                "Observation: Model inference complete.",
                {"high_stress_predictions": len(predictions_to_store)},
            )

            # --- Action 3: Store Predictions ---
            if predictions_to_store:
                self._log("Initiating action: Store predictions in DynamoDB.")
                items_inserted = store_predictions(predictions_to_store, file_path)
                self._log(
                    "Observation: Storage complete.", {"items_inserted": items_inserted}
                )
            else:
                self._log("Observation: No high-stress predictions to store.")

        except Exception as e:
            self._log("An unexpected error occurred during the run.", {"error": str(e)})

        finally:
            self._log("Agent run finished.")
            print("--- Agent Trace ---")
            print(json.dumps(self.trace, indent=2))
            print("-------------------")
