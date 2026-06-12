import os
import json

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_community.retrievers import BM25Retriever
from document_loader import DocumentLoader
from role_config import ROLE_DOCUMENT_MAP

# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------
DB_LOCATION = "./chroma_langchain_db"
DOCUMENTS_DIRECTORY = "./documents/"
FILE_TYPES = [".pdf", ".docx", ".txt", ".csv", ".md", ".xlsx", ".xls", ".json"]

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

_ROLES = list(ROLE_DOCUMENT_MAP.keys())  # derived from role_config — no hardcoding
_collections: dict[str, Chroma] = {}


def initialize_vector_store(reload: bool = False) -> None:
    """Create one ChromaDB collection per role and ingest documents into the right collection."""
    global _collections

    _collections = {
        role: Chroma(
            collection_name=f"role_{role}",
            persist_directory=DB_LOCATION,
            embedding_function=embeddings,
        )
        for role in _ROLES
    }

    total_chunks = sum(c._collection.count() for c in _collections.values())
    add_documents = reload or total_chunks == 0
    if not add_documents:
        return

    print("Loading documents into vector store...")
    documents, ids = DocumentLoader.load_documents_from_directory(
        directory=DOCUMENTS_DIRECTORY,
        file_types=FILE_TYPES,
    )

    # Bucket each document into its role's collection
    buckets: dict[str, tuple[list, list]] = {role: ([], []) for role in _ROLES}
    for doc, id_ in zip(documents, ids):
        allowed_roles = json.loads(doc.metadata.get("allowed_roles", "[]"))
        for role in _ROLES:
            if role in allowed_roles:
                buckets[role][0].append(doc)
                buckets[role][1].append(id_)
                break  # each doc belongs to exactly one non-admin role

    for role, (docs, doc_ids) in buckets.items():
        if not docs:
            continue
        for i in range(0, len(docs), 2):
            _collections[role].add_documents(
                documents=docs[i:i + 2],
                ids=doc_ids[i:i + 2],
            )
        print(f"  '{role}': {len(docs)} chunks added.")


def get_retriever_for_role(role: str, k: int = 10):
    """Return a hybrid (BM25 + vector) retriever scoped to the given role's collection.
    BM25 handles exact entity lookups (names, IDs); vector search adds semantic coverage.
    Admin merges results from all collections."""
    if not _collections:
        raise RuntimeError("Vector store not initialized. Call initialize_vector_store() first.")

    if role == "admin":
        return _AdminMergedRetriever(stores=list(_collections.values()), k=k)

    if role not in _collections:
        raise ValueError(f"Unknown role: {role}")

    collection = _collections[role]
    vector_retriever = collection.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k},
    )

    # Load all persisted docs for BM25 — exact token matching for names and IDs
    raw = collection._collection.get(include=["documents", "metadatas"])
    bm25_docs = [
        Document(page_content=text, metadata=meta or {})
        for text, meta in zip(raw["documents"], raw["metadatas"])
    ]

    if not bm25_docs:
        return vector_retriever

    bm25_retriever = BM25Retriever.from_documents(bm25_docs, k=k)
    return _EnsembleRetriever(
        retrievers=[bm25_retriever, vector_retriever],
        weights=[0.5, 0.5],
        k=k,
    )


class _EnsembleRetriever(BaseRetriever):
    """Merges two retrievers using Reciprocal Rank Fusion (replaces langchain EnsembleRetriever)."""

    retrievers: list
    weights: list
    k: int = 10

    def _get_relevant_documents(self, query: str, *, run_manager=None) -> list[Document]:
        rrf_k = 60
        scores: dict[str, float] = {}
        docs_by_key: dict[str, Document] = {}
        for retriever, weight in zip(self.retrievers, self.weights):
            for rank, doc in enumerate(retriever.invoke(query)):
                key = doc.page_content
                scores[key] = scores.get(key, 0.0) + weight / (rrf_k + rank + 1)
                docs_by_key.setdefault(key, doc)
        return [docs_by_key[k] for k in sorted(scores, key=lambda x: scores[x], reverse=True)][: self.k]


class _AdminMergedRetriever(BaseRetriever):
    """Queries all role collections and returns the top-k results by relevance score."""

    stores: list
    k: int

    def _get_relevant_documents(self, query: str, *, run_manager=None) -> list[Document]:
        scored = []
        for store in self.stores:
            results = store.similarity_search_with_relevance_scores(query, k=self.k)
            scored.extend(results)
        scored.sort(key=lambda x: x[1], reverse=True)
        return [doc for doc, _ in scored[:self.k]]
