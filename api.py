"""
FastAPI interface for LocalAIAgentWithRAG.

Runs alongside the CLI (main.py) — both share the same vector store,
chain logic, guardrails, and audit log.

Start the server:
    uvicorn api:app --host 0.0.0.0 --port 8000 --reload

Endpoints:
    GET  /health        — liveness check
    POST /chat          — ask a question (JWT required)
    POST /reload        — re-index documents (admin JWT required)
"""

import asyncio
import os
from contextlib import asynccontextmanager

import jwt as pyjwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from audit import log_login, log_query
from auth import VALID_ROLES, SECRET_KEY
from guardrails import (
    _REDIRECT_MESSAGE,
    check_input,
    check_output,
    is_irrelevant_response,
)
from main import build_chain
from vector import get_retriever_for_role, initialize_vector_store

# ------------------------------------------------------------------
# Startup / shutdown
# ------------------------------------------------------------------

_retrievers: dict = {}
_chains: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_vector_store()
    yield


app = FastAPI(
    title="LocalAIAgent RAG API",
    description="Role-scoped document Q&A — all inference runs locally via Ollama.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------
# Auth dependency — converts SystemExit from verify_token to HTTP 401
# ------------------------------------------------------------------

security = HTTPBearer()


def _verify(token: str) -> dict:
    """Replicate auth.verify_token but raise ValueError instead of sys.exit."""
    if not SECRET_KEY:
        raise ValueError("JWT_SECRET_KEY environment variable is not set.")
    try:
        payload = pyjwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except pyjwt.ExpiredSignatureError:
        raise ValueError("Token has expired.")
    except pyjwt.InvalidTokenError as e:
        raise ValueError(f"Invalid token — {e}")

    role = payload.get("role", "")
    if role not in VALID_ROLES:
        raise ValueError(f"Unknown role '{role}'.")

    return {
        "user_id": payload["sub"],
        "role": role,
        "email": payload.get("email", ""),
    }


def get_identity(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    try:
        return _verify(credentials.credentials)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


def require_admin(identity: dict = Depends(get_identity)) -> dict:
    if identity["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required.",
        )
    return identity


# ------------------------------------------------------------------
# Chain cache — one retriever + chain per role, built on first use
# ------------------------------------------------------------------

def _get_chain(role: str):
    if role not in _chains:
        retriever = get_retriever_for_role(role)
        _retrievers[role] = retriever
        _chains[role] = build_chain(retriever)
    return _retrievers[role], _chains[role]


# ------------------------------------------------------------------
# Response parsing — split LLM output into answer text + source list
# ------------------------------------------------------------------

def _parse_response(raw: str) -> tuple[str, list[str]]:
    if "Sources:" not in raw:
        return raw.strip(), []
    answer_part, sources_part = raw.split("Sources:", 1)
    sources = [
        line.lstrip("- ").strip()
        for line in sources_part.splitlines()
        if line.strip().startswith("-")
    ]
    return answer_part.strip(), sources


# ------------------------------------------------------------------
# Request / response models
# ------------------------------------------------------------------

class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]
    role: str
    user_id: str
    warnings: list[str] = []


class HealthResponse(BaseModel):
    status: str


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(
    request: ChatRequest,
    identity: dict = Depends(get_identity),
):
    user_id = identity["user_id"]
    role = identity["role"]
    question = request.question.strip()

    # Input guardrail
    valid, rejection = check_input(question)
    if not valid:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=rejection)

    retriever, chain = _get_chain(role)

    # Retrieval + audit (blocking IO — run in thread pool)
    retrieved_docs = await asyncio.to_thread(retriever.invoke, question)
    log_query(user_id, role, question, retrieved_docs)

    # LLM inference (blocking — run in thread pool)
    raw_answer = await asyncio.to_thread(chain.invoke, question)

    if is_irrelevant_response(raw_answer):
        return ChatResponse(
            answer=_REDIRECT_MESSAGE,
            sources=[],
            role=role,
            user_id=user_id,
        )

    warnings = check_output(raw_answer)
    answer_text, sources = _parse_response(raw_answer)

    return ChatResponse(
        answer=answer_text,
        sources=sources,
        role=role,
        user_id=user_id,
        warnings=warnings,
    )


@app.post("/reload", tags=["System"])
async def reload_documents(identity: dict = Depends(require_admin)):
    """Re-index all documents from disk. Admin only."""
    _chains.clear()
    _retrievers.clear()
    await asyncio.to_thread(initialize_vector_store, True)
    return {"status": "reloaded"}
