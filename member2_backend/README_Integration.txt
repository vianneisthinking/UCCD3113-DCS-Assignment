MEMBER 2 BACKEND — INTEGRATION GUIDE

This package contains the backend API and business logic for the AI customer-support
ticket classification and routing system. It authenticates users, stores complaints,
asks Member 3's AI service to classify them, routes them to a department with a
response deadline, and serves both the customer site and the staff dashboard.

REQUIRED SOFTWARE
- Windows
- Python 3.11

FIRST-TIME SETUP
1. Extract the ZIP file.
2. Open the extracted Member2_Backend folder.
3. Double-click setup_backend.bat.
4. Wait until package installation finishes. Demo data is loaded automatically.

STARTING THE BACKEND
1. Double-click start_backend.bat.
2. Keep the terminal window open.
3. Open http://127.0.0.1:8001/health
4. Confirm that "database" shows "connected".
5. Open http://127.0.0.1:8001/docs to try the endpoints.

The backend runs on port 8001 because Member 3's AI service uses port 8000.

DEMO ACCOUNTS (created by setup)
   staff      staff@support.com  / staff1234
   customer   alice@example.com  / alice1234

Register your own customer accounts through POST /auth/register. Staff accounts are
deliberately not creatable from the public form.

RUNNING BOTH SERVICES
Member 3's AI service should also be running:
   Member3_AI_Backend\start_api.bat        (port 8000)
   Member2_Backend\start_backend.bat       (port 8001)

The backend does NOT require the AI service to be running. If it is down, complaints
are still accepted and stored with status "pending_classification". This is the
system's reliability guarantee, not a bug — see API_CONTRACT.md.

FOR MEMBER 1 (CUSTOMER FRONTEND)
Read API_CONTRACT.md. The endpoints you need:
   POST /auth/register      create an account
   POST /auth/login         returns access_token
   POST /tickets            submit a complaint
   GET  /tickets            the logged-in customer's own tickets
   GET  /tickets/{id}       one ticket

Send the token on every request after login:
   Authorization: Bearer <access_token>

On the ticket status page, show status "pending_classification" as
"Received - being categorised". It means the submission succeeded.

FOR MEMBER 5 (STAFF DASHBOARD)
Log in with the staff account to receive a staff token. The endpoints you need:
   GET   /tickets                        all tickets
   GET   /tickets?status=open            filter by status
   GET   /tickets?department=Billing and Payment
   GET   /tickets?priority=high
   GET   /tickets?overdue=true           past their SLA deadline
   PATCH /tickets/{id}                   change status
   POST  /tickets/{id}/reclassify        retry the AI for a pending ticket
   GET   /stats                          counts for your charts

/stats returns totals by status, category, priority and department, plus an overdue
count, so the dashboard does not have to count in JavaScript.

FOR MEMBER 4 (DATABASE, CLOUD & DEPLOYMENT)
Tables are created automatically on first start. No manual SQL is required.
The schema is documented at the end of API_CONTRACT.md.

Configuration is read from the .env file. To deploy, set these as environment
variables on the hosting platform:

   DATABASE_URL         postgresql://user:password@host:5432/dbname
   AI_SERVICE_URL       the deployed URL of Member 3's service
   JWT_SECRET           a long random string (change from the default)
   JWT_EXPIRE_MINUTES   1440
   CORS_ORIGINS         the deployed URL of Member 1's frontend

Start command for the hosting platform:
   python -m uvicorn api.main:app --host 0.0.0.0 --port $PORT

The psycopg2-binary package is already in requirements.txt, so switching from local
SQLite to cloud PostgreSQL requires no code change — only DATABASE_URL.

TESTING
While the backend is running, open Command Prompt in this folder and run:
   .venv\Scripts\python.exe test_backend.py

Run it twice: once with Member 3's AI service running, and once with it stopped.
Both runs must pass.

RELOADING DEMO DATA
   .venv\Scripts\python.exe seed.py             adds demo data if the database is empty
   .venv\Scripts\python.exe seed.py --reset     wipes everything and reloads

IMPORTANT
- 127.0.0.1 works only when all services run on the same computer. Replace the local
  URLs with the cloud URLs after deployment.
- Do not commit or share the .env file. Share .env.example instead.
- When zipping this folder for the team, exclude .venv, .env and tickets.db.
