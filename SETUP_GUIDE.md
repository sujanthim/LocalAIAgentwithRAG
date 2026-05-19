
# RAG System with Multi-Document Support

This updated RAG (Retrieval-Augmented Generation) system now supports **PDF, Word, CSV, and Text files**.

## 📦 Updated Requirements

The following libraries have been added to support multiple document formats:
- **`pypdf`** - PDF extraction
- **`python-docx`** - Word document parsing
- **`python-pptx`** - PowerPoint support (optional)

## 🚀 Installation

1. **Update dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Verify installation:**
   ```bash
   pip list | grep -E "pypdf|python-docx|langchain"
   ```

## 📁 Project Structure

```
LocalAIAgentwithRAG/
├── main.py              # Main conversation interface
├── vector.py            # Vector store initialization & retrieval
├── document_loader.py   # Multi-format document loader (NEW)
├── requirements.txt     # Dependencies
├── realistic_restaurant_reviews.csv
└── documents/           # Place documents here
    ├── report.pdf
    ├── guide.docx
    ├── data.txt
    └── reviews.csv
```

## 🔧 How to Use

### Option 1: Load All Documents from a Directory

```python
# In vector.py, set this to your documents folder:
documents_directory = "./documents"  # or any path with your files

# Run main.py
python main.py
```

### Option 2: Load Specific Files

Uncomment in `vector.py`:
```python
specific_files = [
    "report.pdf",
    "manual.docx",
    "data.csv"
]

# Then in the load section:
documents, ids = [], []
for file in specific_files:
    file_docs, file_ids = DocumentLoader.load_single_file(file)
    documents.extend(file_docs)
    ids.extend(file_ids)
```

### Option 3: Reload Documents at Runtime

In the chat interface, type:
```
reload
```

This will reload all documents from disk without restarting the program.

## 📄 Supported File Formats

### PDF Files
- **Extraction:** Page-by-page text extraction
- **Metadata:** Source file name, file type, page info
- **Example:** `presentation.pdf`

### Word Documents (.docx)
- **Extraction:** Paragraph-by-paragraph text
- **Metadata:** Source file name, file type
- **Example:** `report.docx`

### CSV Files
- **Extraction:** Row-by-row text (columns and values)
- **Format:** `Column: Value | Column: Value`
- **Example:** `data.csv`

### Text Files
- **Extraction:** Full file content
- **Metadata:** Source file name, file type
- **Example:** `notes.txt`

## 💡 Usage Examples

### Example 1: Multiple PDFs + CSV
```
Directory structure:
documents/
├── invoice_jan.pdf
├── invoice_feb.pdf
├── customer_data.csv
```

Type in chat: `"Who are the customers from invoice_jan?"`
The system will search all PDFs and CSV for relevant information.

### Example 2: Word Documentation
```
documents/
├── user_guide.docx
├── api_reference.docx
```

Type: `"How do I authenticate?"`
The system will search both Word documents.

### Example 3: Mixed Documents
```
documents/
├── contract.pdf
├── amendments.docx
├── terms.txt
├── history.csv
```

Type: `"What are the payment terms?"`
Searches all file types together.

## ⚙️ Advanced Configuration

### Change Embedding Model
In `vector.py`:
```python
embeddings = OllamaEmbeddings(model="mistral")  # or another model
```

### Change Number of Retrieved Documents
In `vector.py`:
```python
retriever = vector_store.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 10}  # Get 10 instead of 5
)
```

### Change LLM Model
In `main.py`:
```python
model = OllamaLLM(model="neural-chat")  # or another Ollama model
```

## 🔍 Features

✅ **Multi-Format Support** - PDF, DOCX, CSV, TXT
✅ **Flexible Loading** - Directory scanning or specific files
✅ **Rich Metadata** - Track source file, type, and location
✅ **Error Handling** - Graceful failures with informative messages
✅ **Runtime Reload** - Refresh documents without restarting
✅ **Source Attribution** - See which document each answer comes from
✅ **Semantic Search** - Find relevant content using embeddings

## 🐛 Troubleshooting

### Error: "No documents found"
- **Cause:** No supported files in the directory
- **Fix:** Place PDF/DOCX/CSV/TXT files in your documents folder

### Error: "Unsupported file type"
- **Cause:** File extension not recognized
- **Supported:** `.pdf`, `.docx`, `.txt`, `.csv`
- **Fix:** Convert file to supported format

### PDF Extraction Issues
- **Cause:** Encrypted or scanned PDF
- **Fix:** Try converting to different format or using OCR preprocessing

### Memory Issues with Large Files
- **Solution:** Split large documents into smaller chunks before loading
- **Recommendation:** Documents <50MB work best

## 📚 Document Preparation Tips

1. **For PDFs:**
   - Use text-based PDFs (not scanned images)
   - Files work best under 50MB
   - Clear, structured content works better

2. **For Word Documents:**
   - Save as .docx format
   - Use proper paragraph formatting
   - Tables and text are extracted

3. **For CSV Files:**
   - Use standard CSV format
   - Each row becomes a searchable document
   - Headers are included

4. **For Text Files:**
   - Plain UTF-8 text
   - One logical document per file

## 🚦 Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Prepare documents:**
   - Create a `documents/` folder
   - Add PDF, DOCX, CSV, or TXT files

3. **Configure vector.py:**
   ```python
   documents_directory = "./documents"
   ```

4. **Run the system:**
   ```bash
   python main.py
   ```

5. **Ask questions:**
   ```
   Your question: What are the main topics in the documents?
   ```

## 📞 Commands

| Command | Action |
|---------|--------|
| `reload` | Reload all documents from disk |
| `q` | Quit the application |
| Any other text | Ask a question to the RAG system |

## 🎯 Next Steps

1. Add your documents to the `documents/` folder
2. Run `python main.py`
3. Type `reload` to index your documents
4. Start asking questions!

---

**Notes:**
- First run may take a few minutes to process and embed documents
- Subsequent runs use the cached Chroma vector database
- Use `reload` command if you add new documents
- The system works best with English text
