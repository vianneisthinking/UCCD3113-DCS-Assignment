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

IMPORTANT
- The API uses the trained models in models\final.
- Do not move the model files unless main.py is updated.
- 127.0.0.1 works only when the backend and AI API run on the same computer.
- Replace the local URL with the cloud URL after deployment.
