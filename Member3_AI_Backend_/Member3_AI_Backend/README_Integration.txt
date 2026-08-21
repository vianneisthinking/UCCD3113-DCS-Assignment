MEMBER 3 AI BACKEND — INTEGRATION GUIDE

This package contains the AI customer-support ticket classification microservice.

REQUIRED SOFTWARE
- Windows
- Python 3.11

FIRST-TIME SETUP
1. Extract the ZIP file.
2. Open the extracted Member3_AI_Backend folder.
3. Double-click setup_api.bat.
4. Wait until package installation finishes.

STARTING THE API
1. Double-click start_api.bat.
2. Keep the terminal window open.
3. Open http://127.0.0.1:8000/health
4. Confirm that both models are shown as true.
5. Open http://127.0.0.1:8000/docs to test POST /predict.

BACKEND INTEGRATION
Send an HTTP POST request to:
http://127.0.0.1:8000/predict

JSON request:
{
  "complaint": "My parcel is marked as delivered but it never arrived."
}

Read these response fields:
- category
- category_confidence
- priority
- priority_confidence
- model_version

TESTING
While the API is running, open Command Prompt in this folder and run:
.venv\Scripts\python.exe api\test_client.py

MODEL DEVELOPMENT WORKFLOW
The legacy data\customer_support_tickets_expanded.csv file is retained only as
an historical artifact. It is not the official test dataset.

1. Generate the fixed, disjoint datasets:
   .venv\Scripts\python.exe prepare_datasets.py
2. Train and select models using only the training and validation datasets:
   .venv\Scripts\python.exe train_models.py
3. Evaluate the exact saved artifacts once on the locked test dataset:
   .venv\Scripts\python.exe evaluate_models.py
4. Run all automated regression tests:
   .venv\Scripts\python.exe -m unittest discover -s tests -v

The training workflow requires scikit-learn 1.7.2, matching deployment. The
training script does not open the locked test file. Do not retrain after reading
locked-test results.

PRIORITY CONFIDENCE
For ordinary cases, priority_confidence is the selected model probability. A
narrow internal safety policy routes clearly severe financial fraud, account
takeover, large financial harm, and complete multi-user outages to high. A
policy match returns 1.0 as deterministic routing confidence, not as an ML
probability. The external response fields remain unchanged.

IMPORTANT
- The API uses the trained models in models\final.
- Do not move the model files unless main.py is updated.
- 127.0.0.1 works only when the backend and AI API run on the same computer.
- Replace the local URL with the cloud URL after deployment.
