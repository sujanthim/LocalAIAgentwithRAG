# LocalAIAgentWithRAG

A local AI chatbot that answers questions from your company's documents. Users log in with a username and password, and only see documents they are authorised to access. All processing runs on your machine — no data is sent to the cloud.

---

## What you need before starting

Install all of the following before proceeding:

| Requirement | Version | Where to get it |
|-------------|---------|-----------------|
| Python | 3.9 or higher | https://python.org/downloads |
| Ollama | Latest | https://ollama.com/download |
| Git | Any | https://git-scm.com |

Confirm they are installed by running:
```bash
python3 --version
ollama --version
git --version
```

---

## Setup (follow these steps in order)

### Step 1 — Clone the project

```bash
git clone https://github.com/sujanthim/LocalAIAgentwithRAG.git
cd LocalAIAgentwithRAG
```

---

### Step 2 — Create a Python virtual environment

A virtual environment keeps this project's packages separate from your system Python.

```bash
python3 -m venv .venv
source .venv/bin/activate
```

You should see `(.venv)` appear at the start of your terminal prompt. You must run the `source` command each time you open a new terminal to work on this project.

Install all dependencies:
```bash
pip install -r requirements.txt
```

---

### Step 3 — Download the AI models

The chatbot runs AI models locally via Ollama. Download them now (this may take several minutes):

```bash
ollama pull llama3.2
ollama pull mistral
```

`llama3.2` (~2 GB) handles chat. `mistral` (~4 GB) is used for the safety check layer.

**Embedding model (HuggingFace):**

The project uses `all-MiniLM-L6-v2` for document embeddings. This model (~90 MB) downloads automatically from HuggingFace the first time you run the app — no manual step needed. You will need an internet connection for that first run. After that it is cached locally and works offline.

If you see this warning on first run, it is harmless:
```
Warning: You are sending unauthenticated requests to the HF Hub...
```
To silence it, add your `HF_TOKEN` to `.env` (explained in Step 4).

---

### Step 4 — Create your .env file

The project uses a `.env` file to store secrets. This file lives in the project folder and is never committed to version control.

Copy the example file to create your own:
```bash
cp .env.example .env
```

Open `.env` in a text editor. You will see:
```
JWT_SECRET_KEY=your-secret-key-here
HF_TOKEN=hf_your_token_here
```

**Generate a secret key** and paste it as the value for `JWT_SECRET_KEY`:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Your `.env` file should look like:
```
JWT_SECRET_KEY=e6a4c275cdc1a7fecff74759f76d2fde...
HF_TOKEN=hf_...
```

> **Keep `JWT_SECRET_KEY` fixed.** If you change it, all existing sessions will stop working and users will need to log in again.

> **`HF_TOKEN` is optional.** It silences a rate-limit warning from HuggingFace. Get a free token at huggingface.co → Settings → Access Tokens (read-only is enough). Leave it blank if you do not want it.

---

### Step 5 — Create your users

Users are stored in a local SQLite database (`users.db`). The database is created automatically the first time you run the command below.

**Add a user:**
```bash
python3 manage_users.py add --username alice --role hr --email alice@yourcompany.com
```

You will be prompted to type and confirm a password. Passwords are never stored in plain text.

**Roles and what each can access:**

| Role | Documents accessible |
|------|---------------------|
| `hr` | HR policies, employee roster, payroll, training guide, benefits |
| `billing` | Billing records, client directory |
| `public` | Company overview only |
| `admin` | Everything |

Add one user per person. For example:
```bash
python3 manage_users.py add --username bob   --role billing --email bob@yourcompany.com
python3 manage_users.py add --username carol --role public  --email carol@yourcompany.com
python3 manage_users.py add --username admin --role admin   --email admin@yourcompany.com
```

**Other user management commands:**
```bash
# List all users
python3 manage_users.py list

# Change a user's password
python3 manage_users.py change-password --username alice

# Remove a user
python3 manage_users.py delete --username alice
```

**Logging in:**

Once you have created your users and started the app (Step 8), open `http://localhost:8501` in your browser. You will see a login screen asking for a username and password — enter the credentials you created above. Each user only sees documents matching their role.

![Login screen: Username field, Password field, Sign in button]

---

### Step 6 — Add your documents

Place your files in the `documents/` folder. Supported formats:

| Format | Extension |
|--------|-----------|
| PDF | `.pdf` |
| Word | `.docx` |
| Plain text | `.txt` |
| Markdown | `.md` |
| CSV | `.csv` |
| Excel | `.xlsx` `.xls` |
| JSON | `.json` |

**Controlling which role can see each document:**

Open `role_config.py` and add your filename to the appropriate role's list:

```python
ROLE_DOCUMENT_MAP = {
    "hr":      ["HR_POLICIES.md", "employee_roster.csv", "your_hr_doc.pdf"],
    "billing": ["billing_records_2024.csv", "your_billing_doc.xlsx"],
    "public":  ["healthcare_company_overview.md"],
}
```

Any document not listed here is only visible to `admin`.

---

### Step 7 — Start Ollama

Open a terminal and run:
```bash
ollama serve
```

Leave this terminal open and running. Open a new terminal for the next step.

---

### Step 8 — Run the app

Choose one of the three options below.

#### Option A — Web interface (recommended for most users)

```bash
source .venv/bin/activate
streamlit run streamlit_app.py
```

Open `http://localhost:8501` in your browser. Log in with the username and password you created in Step 5.

---

#### Option B — Command line

```bash
source .venv/bin/activate
python3 generate_token.py --role hr --user alice --email alice@yourcompany.com
export AUTH_TOKEN='<paste the token printed above>'
python3 main.py
```

Type your question and press Enter. Type `reload` to re-index documents, or `q` to quit.

---

#### Option C — REST API

```bash
source .venv/bin/activate
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

Generate a token and send a request:
```bash
python3 generate_token.py --role hr --user alice --email alice@yourcompany.com
export AUTH_TOKEN='<paste token here>'

curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the vacation policy?"}'
```

Interactive API docs: `http://localhost:8000/docs`

---

## Adding documents after first run

The chatbot indexes your documents into a local database on first run. When you add or change documents you need to re-index:

- **Web interface:** type `reload` in the chat input
- **CLI:** type `reload` at the `You:` prompt  
- **API:** send `POST /reload` with an admin token

To force a full re-index from scratch:
```bash
rm -rf chroma_langchain_db
```
Then restart the app — indexing runs automatically on startup.

---

## Project structure

```
LocalAIAgentWithRAG/
│
├── .env                     # Your secrets (never committed) ← you create this
├── .env.example             # Template showing required variables
│
├── streamlit_app.py         # Web UI
├── main.py                  # CLI chat interface
├── api.py                   # REST API server
│
├── user_store.py            # User auth (Argon2 + SQLite)
├── manage_users.py          # CLI tool to add/remove users
├── auth.py                  # JWT token verification
├── generate_token.py        # Dev token generator (CLI/API only)
│
├── vector.py                # Document indexing and retrieval
├── document_loader.py       # Reads PDF, DOCX, CSV, etc.
├── role_config.py           # Maps roles to documents ← edit this
│
├── guardrails.py            # 4-layer safety system
├── audit.py                 # Query audit log
├── requirements.txt         # Python dependencies
│
└── documents/               # Put your files here ← add files here
```

---

## Troubleshooting

**"JWT_SECRET_KEY is not set"**  
Make sure your `.env` file exists in the project root and contains `JWT_SECRET_KEY=...`. Run `cat .env` to check.

**"Connection refused" or Ollama not responding**  
Make sure `ollama serve` is running in a separate terminal window.

**Answers seem wrong or documents are missing**  
New documents added after the first run need re-indexing. Type `reload` in the chat, or delete `chroma_langchain_db/` and restart.

**"Invalid username or password"**  
Confirm the user was created with `python3 manage_users.py add` and that the password is typed correctly (case-sensitive).

**Responses are very slow**  
Models run on your CPU without a GPU. `llama3.2` (3B parameters) is the fastest available option. Expect 30–90 seconds per response on most laptops.

---

## Security notes

- `.env` and `users.db` are gitignored and never committed
- Passwords are hashed with Argon2 (memory-hard, GPU-resistant)
- `JWT_SECRET_KEY` must remain secret — rotate it by generating a new key in `.env` and re-creating all user sessions
- `generate_token.py` is for development only — in production, use an identity provider (Auth0, Azure AD, Okta)
- `audit.log` records all queries — restrict its file permissions in a shared environment

---

## License

MIT
