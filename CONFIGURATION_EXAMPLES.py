"""
CONFIGURATION EXAMPLES for document_loader usage

Copy the sections you want to use into your vector.py and main.py
"""

# ============================================================================
# EXAMPLE 1: Load all documents from a specific directory
# ============================================================================

from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from document_loader import DocumentLoader
import os

def example_1_load_all_from_directory():
    """Load all PDF, DOCX, TXT, CSV from a directory."""
    
    embeddings = OllamaEmbeddings(model="llama2")
    db_location = "./chroma_db"
    documents_directory = "./my_documents"  # Change this path
    
    documents, ids = DocumentLoader.load_documents_from_directory(
        directory=documents_directory,
        file_types=['.pdf', '.docx', '.txt', '.csv']
    )
    
    if documents:
        vector_store = Chroma(
            collection_name="all_documents",
            persist_directory=db_location,
            embedding_function=embeddings
        )
        vector_store.add_documents(documents=documents, ids=ids)
        vector_store.persist()
        
        retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 5}
        )
        return retriever


# ============================================================================
# EXAMPLE 2: Load only PDFs and Word documents
# ============================================================================

def example_2_load_only_pdf_and_docx():
    """Load only PDF and DOCX files from a directory."""
    
    embeddings = OllamaEmbeddings(model="llama2")
    db_location = "./chroma_db"
    documents_directory = "./reports"
    
    documents, ids = DocumentLoader.load_documents_from_directory(
        directory=documents_directory,
        file_types=['.pdf', '.docx']  # Only these types
    )
    
    if documents:
        vector_store = Chroma(
            collection_name="reports",
            persist_directory=db_location,
            embedding_function=embeddings
        )
        vector_store.add_documents(documents=documents, ids=ids)
        vector_store.persist()
        
        retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 5}
        )
        return retriever


# ============================================================================
# EXAMPLE 3: Load specific files one by one
# ============================================================================

def example_3_load_specific_files():
    """Load specific files with custom control."""
    
    embeddings = OllamaEmbeddings(model="llama2")
    db_location = "./chroma_db"
    
    specific_files = [
        "contracts/agreement_2024.pdf",
        "manuals/user_guide.docx",
        "data/customer_list.csv",
        "notes/meeting_notes.txt"
    ]
    
    all_documents = []
    all_ids = []
    
    for file_path in specific_files:
        documents, ids = DocumentLoader.load_single_file(file_path)
        all_documents.extend(documents)
        all_ids.extend(ids)
    
    if all_documents:
        vector_store = Chroma(
            collection_name="specific_documents",
            persist_directory=db_location,
            embedding_function=embeddings
        )
        vector_store.add_documents(documents=all_documents, ids=all_ids)
        vector_store.persist()
        
        retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 5}
        )
        return retriever


# ============================================================================
# EXAMPLE 4: Load from multiple directories
# ============================================================================

def example_4_load_from_multiple_directories():
    """Load documents from multiple source directories."""
    
    embeddings = OllamaEmbeddings(model="llama2")
    db_location = "./chroma_db"
    
    directories = [
        "./reports",
        "./documentation",
        "./contracts"
    ]
    
    all_documents = []
    all_ids = []
    id_counter = 0
    
    for directory in directories:
        documents, ids = DocumentLoader.load_documents_from_directory(
            directory=directory,
            file_types=['.pdf', '.docx', '.txt']
        )
        
        # Re-index IDs to ensure uniqueness
        new_ids = [f"{id_counter + i}" for i in range(len(ids))]
        all_documents.extend(documents)
        all_ids.extend(new_ids)
        id_counter += len(ids)
    
    if all_documents:
        vector_store = Chroma(
            collection_name="multi_dir_documents",
            persist_directory=db_location,
            embedding_function=embeddings
        )
        vector_store.add_documents(documents=all_documents, ids=all_ids)
        vector_store.persist()
        
        retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 5}
        )
        return retriever


# ============================================================================
# EXAMPLE 5: Load with custom metadata
# ============================================================================

def example_5_load_with_custom_metadata():
    """Load documents and add custom metadata."""
    
    from langchain_core.documents import Document
    
    embeddings = OllamaEmbeddings(model="llama2")
    db_location = "./chroma_db"
    documents_directory = "./documents"
    
    # Load raw documents
    documents, ids = DocumentLoader.load_documents_from_directory(
        directory=documents_directory,
        file_types=['.pdf', '.docx', '.txt', '.csv']
    )
    
    # Add custom metadata
    for doc in documents:
        doc.metadata['department'] = 'Engineering'  # Add custom field
        doc.metadata['indexed_date'] = '2024-01-15'  # Add custom field
        doc.metadata['is_confidential'] = False      # Add custom field
    
    if documents:
        vector_store = Chroma(
            collection_name="documents_with_metadata",
            persist_directory=db_location,
            embedding_function=embeddings
        )
        vector_store.add_documents(documents=documents, ids=ids)
        vector_store.persist()
        
        retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 5}
        )
        return retriever


# ============================================================================
# EXAMPLE 6: Reload documents dynamically
# ============================================================================

class DynamicVectorStore:
    """Wrapper to reload documents easily."""
    
    def __init__(self, documents_directory="./documents", db_location="./chroma_db"):
        self.documents_directory = documents_directory
        self.db_location = db_location
        self.embeddings = OllamaEmbeddings(model="llama2")
        self.retriever = None
        self.vector_store = None
        self.initialize()
    
    def initialize(self):
        """Initialize or load the vector store."""
        documents, ids = DocumentLoader.load_documents_from_directory(
            directory=self.documents_directory,
            file_types=['.pdf', '.docx', '.txt', '.csv']
        )
        
        self.vector_store = Chroma(
            collection_name="dynamic_documents",
            persist_directory=self.db_location,
            embedding_function=self.embeddings
        )
        
        if documents:
            # Clear existing documents
            try:
                self.vector_store.delete_collection()
            except:
                pass
            
            self.vector_store.add_documents(documents=documents, ids=ids)
            self.vector_store.persist()
        
        self.retriever = self.vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 5}
        )
    
    def reload(self):
        """Reload all documents from disk."""
        print("Reloading documents...")
        self.initialize()
        print("Documents reloaded!")
    
    def get_retriever(self):
        """Get the current retriever."""
        return self.retriever


# Usage in main.py:
# vector_store = DynamicVectorStore(documents_directory="./documents")
# retriever = vector_store.get_retriever()
# 
# # Later, when user types 'reload':
# vector_store.reload()


# ============================================================================
# EXAMPLE 7: Filter by file type during retrieval
# ============================================================================

def example_7_filter_by_file_type():
    """Load documents and filter by type during retrieval."""
    
    from langchain_core.documents import Document
    
    embeddings = OllamaEmbeddings(model="llama2")
    db_location = "./chroma_db"
    documents_directory = "./documents"
    
    documents, ids = DocumentLoader.load_documents_from_directory(
        directory=documents_directory,
        file_types=['.pdf', '.docx', '.txt', '.csv']
    )
    
    vector_store = Chroma(
        collection_name="documents",
        persist_directory=db_location,
        embedding_function=embeddings
    )
    vector_store.add_documents(documents=documents, ids=ids)
    vector_store.persist()
    
    # Create custom retriever that filters
    def get_pdf_only(query):
        """Retrieve only from PDF documents."""
        all_results = vector_store.similarity_search(query, k=10)
        pdf_results = [doc for doc in all_results if doc.metadata.get('file_type') == '.pdf']
        return pdf_results[:5]
    
    return get_pdf_only


# ============================================================================
# QUICK START: Copy this to your vector.py
# ============================================================================

"""
QUICK START FOR vector.py:

from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from document_loader import DocumentLoader
import os

embeddings = OllamaEmbeddings(model="llama2")
db_location = "./chroma_langchain_db"
documents_directory = "./documents"  # Your documents folder

def initialize_vector_store(reload=False):
    global retriever
    
    add_documents = reload or not os.path.exists(db_location)
    
    if add_documents:
        documents, ids = DocumentLoader.load_documents_from_directory(
            directory=documents_directory,
            file_types=['.pdf', '.docx', '.txt', '.csv']
        )
        
        vector_store = Chroma(
            collection_name="documents",
            persist_directory=db_location,
            embedding_function=embeddings
        )
        
        if documents:
            vector_store.add_documents(documents=documents, ids=ids)
            vector_store.persist()
    else:
        vector_store = Chroma(
            collection_name="documents",
            persist_directory=db_location,
            embedding_function=embeddings
        )
    
    retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 5}
    )
    return retriever

retriever = initialize_vector_store()
"""
