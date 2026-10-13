# HR RAG Pipeline — README

Oct 13, 2026 · @testing

## Overview

A production-ready HR document ingestion and retrieval pipeline built on Qdrant, AWS S3, HuggingFace embeddings, and a self-hosted Ollama LLM.

| Component | Technology |
| --- | --- |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` — 384 dims, CPU-friendly |
| Vector store | Qdrant (local Docker or Qdrant Cloud) |
| LLM | Self-hosted Ollama on EC2 (`llama3.2:3b-instruct-q4_K_M` — quantized) |
| Orchestration | LangChain (prompt templates, caching, async) |
| Cache | Redis (LLM response cache, 1-hour TTL) |
| API | FastAPI with async endpoints |
| Storage | AWS S3 (documents organized by RBAC prefix) |

**Key features:**

- Per-format chunking: Markdown (header-aware), PDF (parent-child), CSV, Excel, DOCX, TXT
- Parent-child retrieval for PDFs — precise vector search, full page context to LLM
- RBAC pre-filtering enforced at Qdrant index level — restricted chunks never enter the search space
- Deterministic point IDs — re-ingestion overwrites vectors, never duplicates
- Score threshold filtering (`MIN_SCORE_THRESHOLD=0.20`) — low-confidence results dropped before LLM
- Async LLM generation with Redis caching for fast repeated queries

## Project Structure

```
rag_pipeline/
├── config/
│   └── settings.py          # Env vars, ROLE_PERMISSIONS, score threshold
├── chunkers/
│   ├── __init__.py           # Format router (route_and_chunk)
│   ├── markdown_chunker.py   # Header-aware + recursive splitting
│   ├── pdf_chunker.py        # Parent-child hierarchical chunking
│   ├── tabular_chunker.py    # Row-as-a-chunk (CSV + Excel)
│   ├── docx_chunker.py       # Word document chunking (python-docx)
│   └── text_chunker.py       # Plain text chunking with UTF-8/latin-1 fallback
├── ingestion/
│   ├── s3_loader.py          # Stream documents from S3 by prefix
│   ├── embedder.py           # HuggingFace embeddings, batching + retry
│   ├── qdrant_store.py       # Qdrant upsert, deterministic IDs, collection mgmt
│   └── pipeline.py           # Full and single-document ingest orchestration
├── retrieval/
│   ├── retriever.py          # RBAC-filtered Qdrant search + score threshold
│   └── generator.py          # LangChain + Ollama async answer generation
├── tests/
│   ├── test_chunkers.py
│   └── test_retrieval_rbac.py
├── api.py                    # FastAPI app (async /query endpoint)
├── run_ingest.py             # CLI entrypoint
├── docker-compose.yml        # Qdrant + Redis stack
└── requirements.txt
```

## Setup

**1. Install dependencies**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**2. Configure environment**

```bash
cp .env.example .env
```

```bash
# .env
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSIONS=384

QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=              # leave blank for local
QDRANT_COLLECTION=hr_docs

OLLAMA_URL=http://<YOUR-EC2-IP>:11434
OLLAMA_MODEL=llama3.2:3b-instruct-q4_K_M

AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=ap-south-1
S3_BUCKET=your-bucket-name

MIN_SCORE_THRESHOLD=0.20
```

**3. Start Qdrant + Redis**

```bash
docker compose up qdrant redis -d
```

**4. Verify Ollama on EC2**

```bash
curl http://<YOUR-EC2-IP>:11434/api/tags
```

## S3 Bucket Structure

The S3 prefix determines the RBAC access role — keep documents in the correct prefix.

```
s3://your-bucket/
├── hr/            → HR-Admin only
│   ├── 01_Employee_Handbook_HR_Policies.docx
│   └── 02_Payroll_Compensation_Benefits_Policy.pdf
├── finance/       → Finance + HR-Admin
│   └── budget_2026.xlsx
├── staff/         → All authenticated employees
│   ├── 04_Employee_Induction_Guide.md
│   └── 09_Employee_FAQ.md
└── public/        → Everyone including contractors
    └── public_holidays_2026.csv
```

**Supported formats:** `.md` `.pdf` `.csv` `.xlsx` `.docx` `.txt`

> Files placed under `00_README_*` are excluded from ingestion — they pollute retrieval results.

## Running Ingestion

```bash
# Ingest all documents
python run_ingest.py

# Ingest a specific prefix
python run_ingest.py --prefix hr/

# Re-ingest a single updated document
python run_ingest.py --key hr/01_Employee_Handbook_HR_Policies.docx --reingest

# Re-ingest everything (wipe stale vectors)
python run_ingest.py --reingest
```

> Re-ingestion uses deterministic point IDs — existing vectors are overwritten, never duplicated. Run with `--reingest` whenever a document is updated in S3.

## Running the API

```bash
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

**Query endpoint**

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"employee_id": "EMP001", "question": "What is the minimum password length?", "top_k": 5}'
```

Response:

```json
{
  "answer": "Passwords must be at least 14 characters long...",
  "sources": ["08_IT_and_Information_Security_Policy.txt"],
  "role_used": "HR-Admin"
}
```

**Health check**

```bash
curl http://localhost:8000/health
```

**Re-ingest a single document via API**

```bash
curl -X POST http://localhost:8000/ingest/single \
  -H "Content-Type: application/json" \
  -d '{"key": "hr/01_Employee_Handbook_HR_Policies.docx", "reingest": true}'
```

## Running Tests

```bash
pytest tests/ -v
```

| Test file | What it covers |
| --- | --- |
| `test_chunkers.py` | Markdown, PDF, CSV, Excel, DOCX, TXT chunkers |
| `test_retrieval_rbac.py` | RBAC filtering, score threshold, parent-child promotion |

## Role Hierarchy

| Role | Can see |
| --- | --- |
| `HR-Admin` | HR-Admin + Finance + General-Staff + Public |
| `Finance` | Finance + General-Staff + Public |
| `General-Staff` | General-Staff + Public |
| `Contractor` | Public only |

To modify, edit `ROLE_PERMISSIONS` in `config/settings.py`.

Roles are resolved server-side from `employee_id` — the client never supplies or overrides the role.

## EC2 — Ollama Setup

Ollama runs on a separate EC2 instance serving the quantized LLM.

| Setting | Value |
| --- | --- |
| Instance | `t3.large` (8 GB RAM minimum) |
| Model | `llama3.2:3b-instruct-q4_K_M` (1.9 GB on disk) |
| Port | `11434` — restrict in security group to app server IP only |

```bash
# Bind Ollama to all interfaces (required for external access)
sudo mkdir -p /etc/systemd/system/ollama.service.d
sudo tee /etc/systemd/system/ollama.service.d/override.conf <<EOF
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
EOF

sudo systemctl daemon-reload
sudo systemctl restart ollama

# Verify
ss -tlnp | grep 11434
# Expected: 0.0.0.0:11434

# Pull the model
ollama pull llama3.2:3b-instruct-q4_K_M
```

## Security Notes

- **Role is never trusted from the client.** `employee_id` is resolved server-side to a role. In production, back this with JWT verification (`PyJWT` + your SSO provider's public key).
- **RBAC filter runs before ANN search in Qdrant** — restricted chunks are not filtered from results, they never enter the search space at all.
- **Ollama port 11434** must be restricted in your EC2 security group to your app server's IP only — never open to `0.0.0.0/0`.
- **S3 IAM policies** should prevent unauthorised uploads. The pipeline trusts the prefix → role mapping; an attacker who can upload to `hr/` would bypass RBAC.
- **Score threshold** (`MIN_SCORE_THRESHOLD=0.20`) prevents low-confidence chunks reaching the LLM. Tune upward if you see irrelevant answers.
- **Redis cache TTL** defaults to 1 hour. Reduce it if documents are updated frequently.
- Rotate AWS IAM credentials regularly and use least-privilege roles.

**Qdrant Cloud**

To use Qdrant Cloud instead of local Docker, set in `.env`:

```bash
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your-qdrant-cloud-api-key
```

No other code changes needed.

## docker-compose.yml

```yaml
services:
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru

volumes:
  qdrant_data:
  redis_data:
```

## requirements.txt

```
fastapi
uvicorn[standard]
pydantic
boto3
qdrant-client
langchain
langchain-ollama
langchain-community
langchain-huggingface
sentence-transformers
redis
tenacity
python-dotenv
python-docx
openpyxl
pdfplumber
```
