# LocalAIAgentWithRAG

A local AI agent with Retrieval-Augmented Generation (RAG) built on LangChain, Ollama (local LLMs), and ChromaDB. The system ingests multi-format documents (PDF, DOCX, CSV, TXT) and answers questions using semantic search over embedded document content.

## Architecture

- **LLM**: Ollama (local inference, e.g., `llama2`, `neural-chat`, `mistral`)
- **Embeddings**: `OllamaEmbeddings` via `langchain-ollama`
- **Vector Store**: ChromaDB via `langchain-chroma`, persisted to `./chroma_langchain_db`
- **Document Loader**: `document_loader.py` — custom multi-format loader
- **Entry Point**: `main.py` — interactive CLI chat loop
- **Vector Init**: `vector.py` — sets up embeddings, loads docs, returns retriever

## Key Files

| File | Purpose |
|------|---------|
| `main.py` | Chat loop — authenticates via JWT, audits every query |
| `vector.py` | Initializes ChromaDB and `DocumentLoader`, returns role-filtered retriever |
| `document_loader.py` | Loads PDF, DOCX, CSV, TXT into LangChain `Document` objects with `allowed_roles` metadata |
| `role_config.py` | Role-to-document map and `get_allowed_roles()` helper |
| `auth.py` | JWT verification — extracts `user_id` and `role` from signed token |
| `audit.py` | Structured JSON audit log (`audit.log`) — login and query events |
| `generate_token.py` | Dev-only token generator (simulates an IdP) |
| `requirements.txt` | Python dependencies |
| `documents/` | Drop your files here for ingestion |

## Setup

**Prerequisites**: [Ollama](https://ollama.ai) must be installed and running locally.

```bash
# Pull a model
ollama pull llama2

# Install Python dependencies
pip install -r requirements.txt

# 1. Generate a secret key (do this once, keep it safe)
export JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# 2. Generate a token for a role (simulates IdP login)
python generate_token.py --role hr --user alice --email alice@medcare.com

# 3. Export the token and run
export AUTH_TOKEN='<paste token here>'
python main.py
```

## Chat Commands

| Command | Action |
|---------|--------|
| `reload` | Re-ingest all documents from disk without restarting |
| `q` | Quit |
| Any text | Ask a question — the system retrieves relevant docs and answers |

## Adding Documents

1. Place files in `./documents/` (or configure a different path in `vector.py`)
2. Supported formats: `.pdf`, `.docx`, `.txt`, `.csv`
3. Type `reload` in the chat to re-index

## Configuration

**Change embedding model** (`vector.py`):
```python
embeddings = OllamaEmbeddings(model="mistral")
```

**Change LLM** (`main.py`):
```python
model = OllamaLLM(model="neural-chat")
```

**Change retrieval count** (`vector.py`):
```python
retriever = vector_store.as_retriever(search_kwargs={"k": 10})
```

## Sample Data

The `documents/` folder contains fictional MedCare Billing Solutions data for testing:
- `HR_POLICIES.md`, `TRAINING_COMPLIANCE_GUIDE.md` — HR policy documents
- `employee_roster.csv`, `payroll_summary_2024.csv`, `billing_records_2024.csv`, `benefits_enrollment.csv`, `client_directory.csv` — structured business data
- `healthcare_company_overview.md` — company profile

## Notes

- ChromaDB is persisted to `./chroma_langchain_db` — delete this folder to force a full re-index
- First run takes time to embed all documents
- Large files (>50MB) or scanned/encrypted PDFs may cause issues
- All inference is local — no API keys required
