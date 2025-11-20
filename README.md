# E-Commerce Backend API

FastAPI backend for e-commerce clothing store.

## Setup

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create `.env` file (copy from `.env.example`)

4. Run server:
```bash
uvicorn app.main:app --reload
```

5. Access API docs: http://localhost:8000/docs
