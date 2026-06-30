# GEM Setup Guide

This project has:

- `frontend/` - React + Vite
- `backend/` - FastAPI + SQLite

Run the frontend and backend in two separate terminals.

## Prerequisites

- Node.js 18+ and `npm`
- Python 3.11+ and `pip`

## Backend Setup

Open a terminal in:

```powershell
cd backend
```

Create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Create the environment file:

```powershell
Copy-Item .env.example .env
```

Update `backend/.env` with your values.

Required:

- `OPENROUTER_API_KEY=your-real-openrouter-api-key`
- `SECRET_KEY=your-own-secret-key`

Optional:

- `DATABASE_URL=sqlite:///./gem_ai.db`
- `ALGORITHM=HS256`
- `ACCESS_TOKEN_EXPIRE_MINUTES=1440`
- `OPENROUTER_GENERAL_MODEL=qwen/qwen3-coder:free`
- `OPENROUTER_CODING_MODEL=qwen/qwen3-coder`
- `OPENROUTER_FREE_FALLBACK_MODEL=nvidia/nemotron-3-nano-30b-a3b:free`
- `OPENROUTER_FALLBACK_PROVIDERS=nvidia`
- `OPENROUTER_MAX_TOKENS=4096`
- `OPENROUTER_TIMEOUT_SECONDS=45`
- `OPENROUTER_HTTP_REFERER=http://localhost:5173`
- `OPENROUTER_APP_TITLE=Gem-AI`
- `SMTP_HOST=smtp.gmail.com`
- `SMTP_PORT=587`
- `SMTP_SENDER_EMAIL=your-gmail-address@gmail.com`
- `GOOGLE_APP_PASSWORD=...`
- `OTP_EXPIRY_MINUTES=10`
- `OTP_LENGTH=6`

Start the backend server:

```powershell
uvicorn app.main:app --reload
```

Backend URLs:

- App: `http://localhost:8000`
- Health check: `http://localhost:8000/api/health`
- Docs: `http://localhost:8000/docs`

Notes:

- The SQLite database file `gem_ai.db` is created inside `backend/` on first run.
- Static image files are served from `/static`.
- As of April 24, 2026, the configured free-tier coding model slug is `qwen/qwen3-coder:free` on OpenRouter.
- Forgot-password OTP email uses Gmail SMTP by default. In local debug mode, if SMTP sender config is missing, the API returns a development OTP in the success message so you can still test the reset flow.

## Frontend Setup

Open a second terminal in:

```powershell
cd frontend
```

Install dependencies:

```powershell
npm install
```

Start the frontend:

```powershell
npm run dev
```

Frontend URL:

- App: `http://localhost:5173`

Notes:

- Vite is already configured to proxy `/api` and `/static` to `http://localhost:8000`.
- Because of that, keep the backend running while using the frontend locally.

## Run Both Together

Terminal 1:

```powershell
cd backend
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

Terminal 2:

```powershell
cd frontend
npm install
npm run dev
```

Then open:

```text
http://localhost:5173
```

## Troubleshooting

If PowerShell blocks virtual environment activation:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

If the frontend cannot connect to the backend:

- Make sure the backend is running on port `8000`
- Make sure the frontend is running on port `5173`
- Check that `backend/.env` exists and contains a valid `OPENROUTER_API_KEY`

If `npm install` or `pip install` fails, verify that Node.js and Python are installed and available in your terminal.
