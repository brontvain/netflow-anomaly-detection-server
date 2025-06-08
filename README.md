# Netflow v5 Server with Anomaly Detection

A comprehensive Netflow v5 server that collects, stores, and analyzes network flows with anomaly detection capabilities.

## Features

- Netflow v5 collector and parser
- PostgreSQL database for flow storage
- 5-day data retention policy
- Web UI for flow visualization
- Machine learning-based anomaly detection
- RESTful API endpoints

## Prerequisites

- Python 3.11
- PostgreSQL 12+
- Node.js 16+ (for frontend)

## Setup

1. Create a virtual environment:
```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip3 install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Create the postgres user in PostgreSQL:
```bash
/opt/homebrew/opt/postgresql@14/bin/createuser -s postgres
```

5. Create the netflow database:
```bash
/opt/homebrew/opt/postgresql@14/bin/createdb -U postgres netflow
```

6. Initialize the database:
```bash
python3 scripts/init_db.py
```

7. Start the backend server:
```bash
uvicorn app.main:app --reload
```

8. Start the frontend server:

```bash
source venv/bin/activate
cd frontend
npm install  # Only needed first time
npm start
```

http://localhost:3000