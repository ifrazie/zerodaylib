# Phase 3: Complete Zero Day Librarian MVP

This repository contains the complete Zero Day Librarian MVP with both backend and frontend components.

## Project Structure

```
zerodaylib/
├── backend/               # FastAPI backend with CockroachDB integration
├── frontend/              # Next.js frontend dashboard
├── app/                   # Agent applications
└── README.md
```

## Running the Full Application

### Prerequisites

- Docker (for CockroachDB)
- Python 3.10+
- Node.js 18+
- npm/yarn

### Setup

1. Start CockroachDB:
   ```bash
   docker run -d --name cockroachdb -p 26257:26257 -p 8080:8080 cockroachdb/cockroach:v23.1.0 start-single-node --insecure
   ```

2. Initialize database schema:
   ```bash
   cd backend
   python -m init_db
   ```

3. Install backend dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

4. Install frontend dependencies:
   ```bash
   cd ../frontend
   npm install
   ```

5. Create `.env.local` in frontend:
   ```
   NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
   ```

### Running in Development

1. Start backend:
   ```bash
   cd backend
   python main.py
   ```

2. Start frontend:
   ```bash
   cd ../frontend  
   npm run dev
   ```

3. Open browser to `http://localhost:3000`

### Running in Production

1. Build frontend:
   ```bash
   cd frontend
   npm run build
   ```

2. Start backend:
   ```bash
   cd backend
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

3. Serve frontend:
   ```bash
   cd frontend
   npm run start
   ```

## Hackathon Demo

The application demonstrates:

1. **CVE Ingestion**: Pulls CVE data from NVD feeds
2. **Asset Linking**: Maps vulnerabilities to affected assets
3. **Semantic Memory**: Distributed vector search using CockroachDB's vector indexing
4. **Policy Evaluation**: Governance policies applied to findings
5. **Audit Timeline**: Complete audit trail of all actions

### Demo Workflow

1. Navigate to the Findings Dashboard
2. Select a finding to view details
3. See "Similar Past Findings" from semantic memory
4. Review governance decision status
5. Inspect the complete audit timeline

## Database Schema

### Key Tables

- `findings`: Security findings with CVE mappings
- `semantic_memory`: Prior incidents with vector embeddings
- `timeline`: Audit timeline events
- `assets`: Asset inventory

### CockroachDB Features Used

- Distributed vector indexing for semantic search
- JSONB for flexible incident data
- Time-series data with proper temporal indexing
- Atomic writes with conditional logic

## Hackathon Presentation

For judges, the application showcases:

✅ **Real-world scenario**: Security vulnerability management
✅ **Complete workflow**: Ingestion → Memory → Governance → Timeline
✅ **CockroachDB features**: Distributed queries, vector search, JSONB
✅ **Professional UI**: Clean dashboard with filtering and detail views
✅ **Extract, Load, Process, Analyze**: Full data pipeline

## License

ISC