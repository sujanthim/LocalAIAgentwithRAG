import os

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from auth import verify_token
from audit import log_login, log_query
from vector import initialize_vector_store, get_retriever_for_role
from guardrails import (
    check_input,
    redact_pii,
    requires_human_approval,
    request_human_approval,
    check_output,
    check_output_safety,
    is_irrelevant_response,
    _REDIRECT_MESSAGE,
)

# ------------------------------------------------------------------
# LLM configuration
# ------------------------------------------------------------------
MODEL = "llama3.2"

# ------------------------------------------------------------------
# Prompt
# ------------------------------------------------------------------
PROMPT_TEMPLATE = ChatPromptTemplate.from_template(
    """You are a business data assistant. Your job is to answer questions, summarise, and generate content (such as job descriptions, reports, or summaries) using only the documents provided below.

Rules:
- Base your response strictly on the provided documents. Do not use outside knowledge.
- Do not comment on whether the data is real, fictional, or randomly generated.
- Do not mention that you are an AI or reference your own limitations.
- End your answer with a "Sources:" section. List only the filenames exactly as they appear in the brackets above (e.g. "billing_records_2024.csv"). Use this format:
  Sources:
  - billing_records_2024.csv
- The Sources section must contain only bare filenames. No paths, no URLs, no descriptions, no extra text.
- If the documents do not contain enough information to answer, respond with exactly: "I can only answer questions about company documents. Please ask about HR policies, billing records, or employee information." Do not include a Sources section in this case.

Documents:
{context}

Question:
{question}

Answer:"""
)


def format_docs(docs) -> str:
    parts = []
    for doc in docs:
        source = os.path.basename(doc.metadata.get("source", "unknown"))
        parts.append(f"[{source}]\n{doc.page_content}")
    return "\n\n".join(parts)


def build_chain(retriever):
    llm = ChatOllama(model=MODEL)
    chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | PROMPT_TEMPLATE
        | llm
        | StrOutputParser()
    )
    return chain


def main():
    # ------------------------------------------------------------------
    # Authentication — role comes from a verified JWT, never user input
    # ------------------------------------------------------------------
    token = os.environ.get("AUTH_TOKEN", "").strip()
    if not token:
        token = input("Paste your auth token: ").strip()

    identity = verify_token(token)          # exits on any invalid token
    user_id = identity["user_id"]
    role    = identity["role"]
    email   = identity["email"]

    log_login(user_id, role, email)
    print(f"Authenticated: {user_id} ({email}) — role: {role}")

    # ------------------------------------------------------------------
    # Initialize vector store and retriever
    # ------------------------------------------------------------------
    initialize_vector_store()
    retriever = get_retriever_for_role(role)

    chain = build_chain(retriever)

    # ------------------------------------------------------------------
    # Chat loop
    # ------------------------------------------------------------------
    print("\nType your question (or 'quit' to exit):\n")

    while True:
        question = input("You: ").strip()
        if not question:
            continue
        if question.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        # Layer 1: Deterministic input filter
        valid, rejection = check_input(question)
        if not valid:
            print(f"\nAssistant: {rejection}\n")
            continue

        # Layer 2 (input): Redact PII from the user's question
        question, pii_in = redact_pii(question, output=False)
        if pii_in:
            print(f"[GUARDRAIL] PII removed from input: {', '.join(pii_in)}")

        # Layer 3: Human-in-the-loop for sensitive queries
        if requires_human_approval(question):
            if not request_human_approval(question):
                print("\nAssistant: Query cancelled.\n")
                continue

        # Retrieve docs and audit
        retrieved_docs = retriever.invoke(question)
        log_query(user_id, role, question, retrieved_docs)

        answer = chain.invoke(question)

        if is_irrelevant_response(answer):
            print(f"\nAssistant: {_REDIRECT_MESSAGE}\n")
            continue

        # Layer 2 (output): Redact PII from the LLM response
        answer, pii_out = redact_pii(answer, output=True)
        if pii_out:
            print(f"[GUARDRAIL] PII removed from response: {', '.join(pii_out)}")

        # Structural checks (URL detection, Sources section)
        for w in check_output(answer):
            print(w)

        # Layer 4: Model-based safety check
        is_safe, safety_msg = check_output_safety(answer)
        if not is_safe:
            print(f"[GUARDRAIL] {safety_msg}")
            print(f"\nAssistant: {_REDIRECT_MESSAGE}\n")
            continue

        print(f"\nAssistant: {answer}\n")


if __name__ == "__main__":
    main()
