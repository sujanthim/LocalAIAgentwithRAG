# LocalAIAgentWithRAG

A local AI agent with Retrieval-Augmented Generation (RAG) built on LangChain, Ollama, and ChromaDB. The system ingests company documents and lets authenticated users ask questions, generate summaries, and produce content — all grounded in documents they are authorised to access. No internet connection or API keys required.

---

## Features

- **Fully local** — all inference runs via Ollama; no data leaves your machine
- **Role-based access control** — each user role has its own ChromaDB collection; a billing user never touches HR data at the database level
- **JWT authentication** — roles are cryptographically verified, never trusted from user input
- **Multi-format ingestion** — PDF, DOCX, TXT, Markdown, CSV, Excel, JSON
- **Smart ingestion strategy** — prose documents are chunked; CSV/Excel/JSON are ingested row-by-row so individual records remain searchable
- **Source citation** — every answer includes the filenames it was sourced from
- **Input/output guardrails** — prompt injection detection, off-topic blocking, empty response detection
- **Audit logging** — every login and query is logged with user, role, and retrieved sources
- **Reload without restart** — type `reload` in the chat to re-index documents on the fly

---

## Architecture

```
User query
    │
    ▼
JWT verification (auth.py)
    │
    ▼
Input guardrails (guardrails.py)
    │
    ▼
Role-scoped ChromaDB retriever (vector.py)
    │   Per-role collections: role_hr / role_billing / role_public
    │   Admin: merges all collections
    ▼
LangChain chain: retriever → prompt → Ollama LLM → output parser (main.py)
    │
    ▼
Output guardrails (guardrails.py)
    │
    ▼
Audit log (audit.py)          Answer displayed to user
```

---

## Tech Stack

| Component | Library |
|-----------|---------|
| LLM | Ollama (`llama2`) via `langchain-ollama` |
| Embeddings | `OllamaEmbeddings` |
| Vector store | ChromaDB via `langchain-chroma` |
| Auth | `PyJWT` |
| Document loading | `pypdf`, `python-docx`, `pandas`, `openpyxl` |
| Orchestration | LangChain LCEL |

---

## Project Structure

```
LocalAIAgentWithRAG/
│
├── main.py                  # Entry point — auth, chat loop, chain
├── vector.py                # ChromaDB collections, retriever per role
├── document_loader.py       # Multi-format document ingestion
├── role_config.py           # Role → document access map
├── auth.py                  # JWT verification
├── audit.py                 # Structured audit log
├── guardrails.py            # Input/output guardrails
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
- Python 3.10+

### Installation

```bash
# 1. Pull the LLM
ollama pull llama2

# 2. Clone the repo and install dependencies
pip install -r requirements.txt

# 3. Generate a secret key (keep this safe — never commit it)
export JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# 4. Generate a token for your role
python generate_token.py --role hr --user alice --email alice@company.com

# 5. Export the token and run
export AUTH_TOKEN='<paste token here>'
python main.py
```

> **Windows (PowerShell)**
> ```powershell
> $env:JWT_SECRET_KEY = python -c "import secrets; print(secrets.token_hex(32))"
> $env:AUTH_TOKEN = "<paste token here>"
> python main.py
> ```

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
3. Type `reload` in the chat to re-index without restarting

To restrict a new document to a specific role, add it to the relevant role's list in `role_config.py`.

---

## Chat Commands

| Input | Action |
|-------|--------|
| Any question or task | Answered using role-scoped documents |
| `reload` | Re-ingests all documents from disk |
| `q` / `quit` / `exit` | Quit |

### Example queries

```
What is the parental leave policy?
Summarise the compliance training requirements.
Generate a job description for an HR assistant based on our policies.
What is the billing status for client HOSP005?
```

---

## Guardrails

**Input:**
- Prompt injection attempts (e.g. "ignore previous instructions") are blocked before reaching the LLM
- Clearly off-topic questions are rejected with a redirect message

**Output:**
- Responses with no answer content (sources only) are caught and replaced with a redirect
- Generated URLs are flagged as a warning
- Missing source citations are flagged

---

## Security Notes

- `JWT_SECRET_KEY` must be set as an environment variable — never hardcode or commit it
- `generate_token.py` is a dev-only tool that simulates an IdP. In production, tokens should be issued by Auth0, Okta, or Azure AD
- `audit.log` contains query history — restrict filesystem permissions in production
- `chroma_langchain_db/` is gitignored — delete it to force a full re-index

---

## Resetting the Vector Database

```bash
# Delete and re-index from scratch
Remove-Item -Recurse -Force ./chroma_langchain_db   # PowerShell
rm -rf ./chroma_langchain_db                         # bash/zsh
```

Then run `python main.py` — ingestion starts automatically.

---

## License

MIT
