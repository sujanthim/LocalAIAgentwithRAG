# Interview Preparation — LocalAIAgentWithRAG

---

## Q1 — Walk me through how a user query flows through this system

**Answer:**

1. **Authentication** — `main.py` reads the `AUTH_TOKEN` environment variable and calls `verify_token()` in `auth.py`. The JWT is cryptographically verified using `JWT_SECRET_KEY` and the user's `role` is extracted from the payload. The role is validated against a whitelist — any unknown role is rejected immediately.

2. **Vector store init** — `initialize_vector_store()` in `vector.py` connects to ChromaDB. On first run it ingests all documents from `./documents/`, embeds them using Ollama, and stores the vectors in per-role collections. On subsequent runs it reuses the persisted DB.

3. **Retriever** — `get_retriever_for_role(role)` returns a retriever scoped to only that role's ChromaDB collection. An HR user's retriever never touches billing documents.

4. **Chain** — `build_chain(retriever)` wires together: retriever → format docs → prompt template → LLM → output parser using LangChain's LCEL (LangChain Expression Language).

5. **Query** — The user types a question. The retriever embeds the question and does a semantic similarity search in ChromaDB, returning the top-k most relevant document chunks from that role's collection.

6. **Answer** — The retrieved chunks are injected into the prompt as `{context}`. The LLM reads the context and question, and generates an answer based only on the provided documents.

**Example flow for an HR user asking "What is the parental leave policy?":**
- JWT verified → role = `hr`
- Retriever searches only the `hr` ChromaDB collection
- Returns chunks from `HR_POLICIES.md` most similar to the question
- LLM answers using only those chunks

---

## Q2 — What does it mean to "embed" a document, and why does ChromaDB need embeddings?

**Answer:**

An embedding is a list of numbers (a vector) that represents the *meaning* of a piece of text. For example:

- "parental leave policy" → `[0.23, -0.87, 0.45, ...]`
- "maternity benefits" → `[0.21, -0.85, 0.47, ...]` ← similar numbers = similar meaning
- "billing records" → `[-0.62, 0.34, -0.91, ...]` ← very different numbers = different meaning

ChromaDB stores these vectors at ingestion time. When a user asks a question, the question is also embedded into a vector. ChromaDB then finds the stored chunks whose vectors are closest to the question vector using cosine similarity — this is the semantic search.

**Why this matters:** Without embeddings, the system would have to do keyword matching and would miss that "parental leave" and "maternity benefits" mean the same thing. Embeddings capture *meaning*, not just exact words.

In this project, `OllamaEmbeddings(model="llama2")` in `vector.py` handles all embedding — both at ingestion time and at query time. All inference is local, no API calls.

---

## Q3 — Why does the retriever fetch k×3 candidates before filtering? (Historical context)

**Answer:**

This was the previous design before per-role collections were implemented.

Previously, all documents across all roles were stored in a single ChromaDB collection. Role enforcement happened in Python after retrieval — a `RoleFilteredRetriever` would fetch `k×3` candidates and then discard any the user's role couldn't access.

**The problem:** If you only fetch `k=5` and 3 of those happen to belong to a different role, after filtering you're left with only 2 results — not enough.

**Why `k×3`:** Fetching more candidates gives the filter enough to work with. After discarding inaccessible documents, you still have `k` results.

**Why this was not ideal:** ChromaDB was fetching and scoring documents the user was never going to see — wasted work. Role enforcement was happening at the application layer, not the database layer.

**Current design:** Each role has its own ChromaDB collection. The retriever for a role only searches that collection — no over-fetching, no Python-side filtering. Role isolation is enforced at the database layer.

---

## Q4 — If someone steals a user's JWT token, what can they do and what can they not do?

**Answer:**

**What they CAN do:**
- Query any document that role has access to — if they steal an HR token, they can access all HR documents
- Every query is logged in `audit.log` under the *victim's* user ID, making attribution harder
- Access potentially sensitive information such as PHI (Protected Health Information), payroll data, or employee records

**What they CANNOT do:**
- Access other roles' documents — role filtering is enforced at the ChromaDB collection level
- Escalate privileges to admin — the role is locked inside the signed JWT. Without the `JWT_SECRET_KEY` they cannot modify the payload
- Forge a new token — JWT signing requires the secret key
- Write or delete anything — the system is entirely read-only

**Key mitigation:** Short token expiry (`exp` claim in the JWT) limits the attack window. Once the token expires, it is rejected by `verify_token()` regardless of the content.

---

## Q5 — Why store documents in ChromaDB instead of loading them from disk on every query?

**Answer:**

Three reasons:

1. **Semantic search** — If you pass all documents to the LLM every time, the LLM reads everything regardless of relevance. ChromaDB retrieves only the chunks semantically closest to the question, giving the LLM focused, relevant context.

2. **Performance** — Embedding is expensive. Converting text to vectors via Ollama takes significant time. ChromaDB does this once at ingestion and persists the vectors to disk. At query time you only embed the question — not the documents.

3. **Context window limits** — LLMs have a maximum context window (e.g., 4096 tokens). You physically cannot pass hundreds of documents to the LLM at once. RAG solves this by selecting only the top-k most relevant chunks that fit within the context window.

---

## Q6 — Should CSV rows be chunked the same way as PDF or DOCX?

**Answer:**

No — and doing so is a bug.

PDF and DOCX files contain long continuous prose that needs to be split into manageable chunks. But CSV rows are already atomic — each row is one self-contained record:

```
Bill_ID: BILL005 | Client_ID: HOSP005 | Client_Name: City Medical Center | Amount: 120000
```

If a text splitter cuts this at 1000 characters, you could get:

```
# Chunk 1
Bill_ID: BILL005 | Client_ID: HOSP005 | Client_Name: City Medical

# Chunk 2
Center | Amount: 120000
```

Neither chunk is meaningful on its own. The same applies to Excel rows and JSON objects.

**Fix in this project:** `load_single_file()` in `document_loader.py` skips `_split_documents()` for `.csv`, `.xlsx`, `.xls`, and `.json` files. Each row/object is already the right granularity for embedding.

---

## Q7 — How would you know if the retriever returned the right chunks, and what would you do if it didn't?

**Answer:**

**How to verify:**

Print what the retriever actually fetched before passing it to the LLM:

```python
retrieved_docs = retriever.invoke(question)
for doc in retrieved_docs:
    print(doc.metadata.get("source"), "→", doc.page_content[:100])
```

This shows exactly what context the LLM was given. If the answer is wrong, trace it back to the retrieved chunks first.

**If the wrong chunks come back:**

| Problem | Fix |
|--------|-----|
| Too few results | Increase `k` in `get_retriever_for_role` |
| Wrong documents returned | Query doesn't semantically match data — improve document formatting at ingestion |
| Right document, wrong chunk | Adjust `CHUNK_SIZE` / `CHUNK_OVERLAP` in `document_loader.py` |
| Specific ID (e.g. HOSP005) not found | Use row-wise ingestion so each record is its own searchable document |

**Key principle:** If the LLM gives a wrong answer, the problem is almost always retrieval, not the LLM itself. Debug the retriever first.

---

## Q8 — The system uses one documents folder. What problems appear at scale?

**Answer:**

**Problem 1 — No subdirectory support:**
`load_documents_from_directory` uses `os.listdir()` which only reads the top-level folder. Organizing documents into `./documents/hr/`, `./documents/billing/` etc. would be silently ignored. Fix: replace with `os.walk()` for recursive scanning.

**Problem 2 — Slow re-indexing:**
Embedding thousands of documents via Ollama takes hours. Re-running `reload` re-embeds everything. Fix: track file checksums and only re-embed new or changed files.

**Problem 3 — Search slows as documents grow:**
More vectors in one collection = slower similarity search. Fix: separate ChromaDB collections per department so each search operates over a smaller, focused index.

**Ideal architecture at scale:**
- Organize documents into department subfolders
- One ChromaDB collection per department/role
- Role's retriever searches only its collection
- Admin retriever merges results across all collections
- File checksums prevent redundant re-embedding

---

## Q9 — How can the audit log itself become a security risk?

**Answer:**

**Risk 1 — Queries contain sensitive data:**
The audit log records raw query text. If a user types "What is John Smith's salary?" or "Show me patient records for HOSP005", that string is persisted in `audit.log` forever. A compromised log file is a secondary data breach — sensitive information exposed even if the vector DB is secure.

**Risk 2 — Access pattern exposure:**
Even without query content, the log reveals who queried what role and when. This can expose org structure, active investigations, or who has elevated access.

**Risk 3 — No access controls on the log file:**
`audit.log` sits on disk with no encryption or permission restrictions. Any process or user with filesystem access can read it.

**Mitigations:**

| Risk | Mitigation |
|------|-----------|
| Sensitive queries logged | Redact PII before logging — log intent, not raw text |
| Log file exposed | Restrict file permissions; ship logs to a secured SIEM |
| Log tampering | Write to an append-only store |
| Logs stored forever | Retention policy — auto-delete after 90 days |

---

## Q10 — Explain this project in two sentences to a non-technical stakeholder

**Answer:**

> "It is an AI chatbot that answers questions about your company's documents without connecting to the internet — all data stays on your own machine. It only shows each user information relevant to their role, so an HR employee cannot see billing data and vice versa."

**Why this works:**
- "Without connecting to the internet" — covers local inference via Ollama and data privacy
- "Only shows information relevant to their role" — covers role-based access control
- The concrete example makes the security claim tangible for a non-technical audience

---

## Key Concepts to Study Further

| Topic | Why it matters |
|-------|---------------|
| Vector embeddings and cosine similarity | Foundation of how semantic search works |
| JWT structure — header, payload, signature | Understanding what can and cannot be tampered with |
| RAG retrieval debugging | Most common real-world RAG problem |
| ChromaDB metadata filtering | How `where` clauses enforce access at the DB layer |
| LangChain LCEL chains | How retriever → prompt → LLM → parser are wired together |
