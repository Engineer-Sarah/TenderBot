# Run TenderBot locally

## Backend (terminal 1, folder = repo root)
    python -m venv venv
    venv\Scripts\activate          # Windows   (Mac/Linux: source venv/bin/activate)
    pip install -r requirements.txt
    copy env.example .env          # then put your GEMINI_API_KEY and SERPER_API_KEY inside .env
    uvicorn api:app --reload --port 8000

## Frontend (terminal 2)
    cd frontend
    npm install
    npm run dev                    # opens http://localhost:5173

If the backend is not running the frontend shows demo data (yellow badge).
With the backend running the badge turns green ("Live data from backend").
