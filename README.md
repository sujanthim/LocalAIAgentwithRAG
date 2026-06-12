# LocalAIAgentWithRAG

A local AI agent with Retrieval-Augmented Generation (RAG) built on LangChain, Ollama, and ChromaDB. The system ingests company documents and lets authenticated users ask questions, generate summaries, and produce content — all grounded in documents they are authorised to access.

---

## Features

- **Role-based access control** — each user role has its own ChromaDB collection; a billing user never touches HR data at the database level
- **JWT authentication** — roles are cryptographically verified, never trusted from user input
- **Multi-format ingestion** — PDF, DOCX, TXT, Markdown, CSV, Excel, JSON
- **Hybrid retrieval** — BM25 (exact keyword match) + vector search (semantic), merged with Reciprocal Rank Fusion
- **4-layer guardrails** — deterministic input filter, PII redaction, human-in-the-loop approval, model-based safety check
- **Source citation** — every answer includes the filenames it was sourced from
- **Audit logging** — every login and query is logged with user, role, and retrieved sources
- **REST API** — FastAPI server with JWT-protected `/chat` and admin-only `/reload` endpoints
- **Reload without restart** — type `reload` in the CLI chat to re-index documents on the fly

---

## Architecture

```
User query
    │
    ▼
JWT verification (auth.py)
    │
    ▼
Layer 1 — Deterministic input filter      ← blocks injection & off-topic queries
    │
    ▼
Layer 2 — PII redaction (input)           ← strips emails, phone numbers
    │
    ▼
Layer 3 — Human-in-the-loop approval      ← prompts confirmation for sensitive queries
    │
    ▼
Role-scoped hybrid retriever (vector.py)
    │   BM25 + ChromaDB vector search, merged with RRF
    │   Per-role collections: role_hr / role_billing / role_public
    │   Admin: merges all collections
    ▼
LangChain chain: retriever → prompt → Ollama LLM → output parser (main.py)
    │
    ▼
Layer 2 — PII redaction (output)          ← strips SSNs, card numbers from response
    │
    ▼
Layer 4 — Model-based safety check        ← LLM evaluates response for safety (SAFE/UNSAFE)
    │
    ▼
Audit log (audit.py)          Answer displayed to user
```

---

## Tech Stack

| Component | Library / Model |
|-----------|----------------|
| LLM | Ollama (`llama3.2`) via `langchain-ollama` |
| Embeddings | `all-MiniLM-L6-v2` via `langchain-huggingface` (runs locally, no Ollama required) |
| Vector store | ChromaDB via `langchain-chroma` |
| Keyword search | BM25 via `langchain-community` |
| REST API | FastAPI + Uvicorn |
| Auth | PyJWT (HS256) |
| Document loading | `pypdf`, `python-docx`, `pandas`, `openpyxl` |
| Orchestration | LangChain LCEL |

---

## Project Structure

```
LocalAIAgentWithRAG/
│
├── main.py                  # CLI entry point — auth, chat loop, chain
├── api.py                   # FastAPI server — /health, /chat, /reload
├── vector.py                # ChromaDB collections, hybrid retriever per role
├── document_loader.py       # Multi-format document ingestion
├── role_config.py           # Role → document access map
├── auth.py                  # JWT verification
├── audit.py                 # Structured audit log
├── guardrails.py            # 4-layer guardrail system
├── generate_token.py        # Dev token generator (simulates IdP)
├── requirements.txt
│
└── documents/               # Drop your files here
    ├── HR_POLICIES.md
    ├── TRAINING_COMPLIANCE_GUIDE.md
    ├── employee_roster.csv
    ├── payroll_summary_2024.csv
    ├── benefits_enrollment.csv
    ├── billing_records_2024.csv
    ├── client_directory.csv
    └── healthcare_company_overview.md
```

---

## Setup

### Prerequisites

- [Ollama](https://ollama.ai) installed and running
- Python 3.9+

### Installation

```bash
# 1. Pull the models
ollama pull llama3.2
ollama pull mistral

# 2. Start Ollama
ollama serve

# 3. Clone the repo and create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt
```

### Environment variables (persistent)

Add these to `~/.zshrc` so they survive across terminal sessions:

```bash
export JWT_SECRET_KEY="your-secret-key-here"   # generate once, keep fixed
export HF_TOKEN="hf_..."                        # optional — silences HuggingFace rate-limit warnings
```

Generate a secret key once and paste the output into `~/.zshrc`:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Apply to the current terminal:
```bash
source ~/.zshrc
```

> **Important:** `JWT_SECRET_KEY` must stay fixed. Changing it invalidates all existing tokens and requires regenerating them.

### Running the CLI

```bash
# Generate a token for your role
python3 generate_token.py --role hr --user alice --email alice@company.com

# Export the token and run
export AUTH_TOKEN='<paste token here>'
python3 main.py
```

### Running the API server

The server terminal must have `JWT_SECRET_KEY` set before starting:

```bash
source ~/.zshrc
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

Interactive API docs: `http://localhost:8000/docs`

---

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/health` | None | Liveness check |
| `POST` | `/chat` | Any role JWT | Ask a question |
| `POST` | `/reload` | Admin JWT only | Re-index all documents |

**Example:**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the parental leave policy?"}'
```

To test from a browser, use the Swagger UI at `http://localhost:8000/docs` — click **Authorize**, paste your token (no `Bearer` prefix), then use **Try it out** on any endpoint.

---

## Roles

| Role | Documents accessible |
|------|---------------------|
| `hr` | HR policies, employee roster, payroll, training guide, benefits |
| `billing` | Billing records, client directory |
| `public` | Company overview |
| `admin` | All documents |

To add a new role, update `ROLE_DOCUMENT_MAP` in `role_config.py` — a new ChromaDB collection is created automatically on next run.

---

## Adding Documents

1. Place files in `./documents/`
2. Supported formats: `.pdf`, `.docx`, `.txt`, `.md`, `.csv`, `.xlsx`, `.xls`, `.json`
3. Type `reload` in the CLI chat, or call `POST /reload` (admin only) via the API

To restrict a document to a specific role, add its filename to the relevant role's list in `role_config.py`.

---

## Guardrails

Queries pass through four layers before and after the LLM:

| Layer | Stage | What it does |
|-------|-------|-------------|
| **1 — Deterministic input filter** | Before LLM | Blocks prompt injection attempts and off-topic questions via regex |
| **2 — PII redaction (input)** | Before LLM | Strips emails and phone numbers from user queries |
| **3 — Human-in-the-loop** | Before LLM | Prompts for confirmation on queries involving salary, SSN, payroll, or termination |
| **2 — PII redaction (output)** | After LLM | Strips SSNs, card numbers, and bank account numbers from responses |
| **4 — Model-based safety** | After LLM | Sends the response to `llama3.2` for a `SAFE`/`UNSAFE` verdict; blocks unsafe responses |

---

## CLI Commands

| Input | Action |
|-------|--------|
| Any question | Answered using role-scoped documents |
| `reload` | Re-ingests all documents from disk |
| `q` / `quit` / `exit` | Quit |

**Example queries:**
```
What is the parental leave policy?
Summarise the compliance training requirements.
Generate a job description for an HR assistant based on our policies.
What is the billing status for client HOSP005?
```

---

## Security Notes

- `JWT_SECRET_KEY` must be a fixed value in your environment — never hardcode or commit it
- `generate_token.py` is a dev-only tool. In production, tokens should come from an IdP (Auth0, Okta, Azure AD)
- `audit.log` contains query history — restrict filesystem permissions in production
- `chroma_langchain_db/` is gitignored — delete it to force a full re-index (required when changing documents or embedding model)

---

## Resetting the Vector Database

```bash
rm -rf ./chroma_langchain_db
python3 main.py   # re-ingestion starts automatically
```

---

## License

MIT
