# Zero Day Librarian - Frontend Dashboard

This is the Next.js frontend for the Zero Day Librarian MVP demo.

## Setup

```bash
cd frontend
npm install
```

## Configuration

Create a `.env.local` file with your backend API URL:

```env
NEXT_PUBLIC_API_CASE_URL=http://localhost:8000
```

## Running the Development Server

```bash
npm run dev
```

The app will be available at `http://localhost:3000`

## Building for Production

```bash
npm run build
npm run start
```

## Key Features

- **Findings Dashboard**: View all CVE findings with filtering by status and severity
- **Finding Detail**: See detailed information about each finding
- **Semantic Memory**: View similar past findings retrieved from the distributed vector index (CockroachDB)
- **Governance Tracking**: Monitor governance decision status
- **Audit Timeline**: Complete workflow trace showing the CVE ingestion → asset link → memory retrieval → policy evaluation process

## Technology Stack

- Next.js 14 with TypeScript
- React 18
- Tailwind CSS for styling
- CockroachDB for backend data storage
- FastAPI backend integration

## Hackathon Demo Focus

This minimal UI showcases the core MVP scenario:

1. CVE ingestion from NVD feeds
2. Asset linking and inventory association
3. Semantic memory retrieval with distributed vector indexing
4. Policy-based governance evaluation
5. Complete audit timeline tracking

The interface is designed to be clean, professional, and easy for hackathon judges to understand the end-to-end workflow.

## Connecting to Backend

The frontend connects to the FastAPI backend endpoints:
- `/api/findings` - List and filter findings
- `/api/findings/{id}` - Get finding details
- `/api/semantic-memory/{id}` - Retrieve similar past findings
- `/api/governance/{id}` - Get governance status
- `/api/audit/{id}` - Get audit timeline

All API calls are made through the `src/lib/api.ts` client.

## License

ISC