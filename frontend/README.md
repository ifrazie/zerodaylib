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

> **Edited a route's `generateStaticParams` / `dynamicParams` exports?** Restart the dev server
> with the cache cleared. Next.js's dev server caches route metadata and does not hot-reload
> those exports, which surfaces as: `Page "/finding/[id]/page" is missing exported function
> "generateStaticParams()"`.
>
> - **Full stack (recommended):** from the **repo root**, run `npm run dev:clean` — clears the
>   `.next` cache and starts the backend + frontend together.
> - **Frontend only:** from this folder, run `npm run dev:frontend:clean`.

## Building for Production

```bash
# Static export → out/ (used by the CDK frontend stack)
npm run build:clean   # wipes .next/out first, then builds — avoids stale-cache export errors
# or, if you know the cache is clean:
npm run build
```

Useful scripts:

| Script | Run from | Purpose |
|--------|----------|---------|
| `npm run dev:clean` | **repo root** | Clear `.next`, then start **backend + frontend** together (use after editing route exports) |
| `npm run dev` | repo root | Start backend + frontend together |
| `npm run dev` | frontend | Start the frontend dev server only |
| `npm run dev:frontend:clean` | frontend | Clear `.next`, then start the frontend only |
| `npm run build` | frontend | Static `output: export` production build → `out/` |
| `npm run build:clean` | frontend | Clear `.next`/`out`, then build (safest for deployment) |
| `npm run clean` | frontend | Remove `.next` and `out` |

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