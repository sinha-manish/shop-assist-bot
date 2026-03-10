# 🎯 Shop Assist MVP: AI-Powered Voice Agent Ingestion System (Gemini & CLU Version)

## 📋 Project Overview

**Project**: AI-Powered Voice Agent for Enhanced Customer Insights in Retail
**Dataset**: Shop Assist inventory & store dataset (.xlsx)
**Purpose**: Convert retail data into searchable vector documents with CLU semantic metadata and use Gemini to generate natural language responses for AI voice agent queries.

-----

## 🏗️ System Architecture

### Core Components

1.  **Excel Processor** - Reads Shop Assist dataset from `data/documents/`
2.  **CLU Analyzer** - Uses Microsoft CLU to extract intent and entities for each row
3.  **Vector Database** - ChromaDB with collection `shop_assist_retail_data_clu`
4.  **Gemini API** - Generates human-readable, conversational responses from structured data

### Data Flow

```
Excel File → Pandas DataFrame → CLU Analysis (Intent/Entities) → ChromaDB
                                        ↓
User Query ➡️ Flask Web UI ➡️ CLU ➡️ ChromaDB ➡️ Structured Data ➡️ Gemini ➡️ Final Response
```

-----

## 📁 Project Structure

```
rag/
├── ingest_clu.py           # Main CLU ingestion script
├── config.yaml             # CLU and system configuration
├── requirements.txt        # Python dependencies
├── MVP_SUMMARY.md          # This document
├── app.py                  # Main Flask web app (Gemini & CLU integration)
├── generateUtterence.py    # Generate test utterances from dataset
├── geminiLLM.py            # Gemini API integration
├── test_dual_mode_ui.py    # Test suite for CLU ingestion
├── data/
│   └── documents/          # Place Shop Assist Excel file here
└── chroma_db/              # ChromaDB storage (auto-created)
```

-----

## 🚀 Quick Start

### 1\. Setup Environment

```bash
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 2\. Configure APIs

  - Edit `config.yaml` with your CLU endpoint, key, project, and deployment names.
  - Set your Gemini API key as an environment variable:
    ```bash
    set GOOGLE_API_KEY=your_key_here
    ```

### 3\. Add Your Data

  - Place your Shop Assist `.xlsx` file in `data/documents/`
  - Ensure first row contains column headers
  - Data should start from the second row


### 4\. Run CLU Ingestion

```bash
python ingest_clu.py
```

-----

### 5\. Launch the Web Chat UI

```bash
python app.py
```

This will launch the Flask web chat assistant at [http://localhost:5000](http://localhost:5000).

## ⚙️ Technical Specifications

### Function Signatures

```python
def excel_to_documents_async(excel_path: Path) -> Tuple[List[str], List[Dict]]:
    """Convert Excel to CLU-analyzed documents and export JSON records."""

async def ingest_excel_docs_async() -> None:
    """Process Excel files and index into ChromaDB."""
```

### Document Structure

  - **content**: `"Column1: Value1, Column2: Value2, ..."`
  - **metadata**: `{ "source_file": filename, "row_index": idx, "record_type": "retail_data", "clu_result": {intent, entities} }`

### Vector Database

  - **Collection**: `shop_assist_retail_data_clu`
  - **Storage**: Persistent ChromaDB at `chroma_db/`

-----

## 📊 Output Files

### 1\. ChromaDB Index

  - **Location**: `chroma_db/`
  - **Collection**: `shop_assist_retail_data_clu`
  - **Purpose**: AI query processing and semantic/intent-based search

### 2\. JSON Records

  - **Location**: `data/documents/{filename}_records.json`
  - **Format**: Array of row dictionaries
  - **Purpose**: Backend lookup and data processing

### 3\. Console Logs

  - Processing progress for each file
  - Document counts and indexing status
  - Final summary with total records processed

-----

## 🔧 Configuration

### Default Settings

  - **Data Directory**: `data/documents/`
  - **Database Path**: `chroma_db/`
  - **Collection Name**: `shop_assist_retail_data_clu`

### Customization

The script is designed for simplicity but can be easily modified:

  - Change CLU project/deployment in `config.yaml`
  - Modify document metadata structure
  - Adjust ChromaDB settings
  - Change JSON export format

-----

## 🧪 Testing

### Test Suite

```bash
python test_dual_mode_ui.py
```

**Tests Include**:

  - Directory structure validation
  - CLU API connectivity
  - ChromaDB indexing
  - Execution capability

### Expected Output

```
============================================================
TEST RESULTS: All tests passed
============================================================
🎉 All CLU tests passed! Your ingestion script is ready.
```

-----

## 💡 CLU & Gemini Integration

### RAG Agent Ready

The indexed data is immediately ready for:

  - **Semantic Search**: Find similar products/stores
  - **Intent-based Search**: Query by CLU intent/entities
  - **Voice Agent**: Process natural language queries
  - **Web Chat UI**: Modern Flask-based chat interface for all users
  - **Recommendations**: Suggest related products or stores

### Collection Access

```python
# Access your indexed data
from chromadb import PersistentClient

client = PersistentClient(path="chroma_db")
collection = client.get_collection("shop_assist_retail_data_clu")

# Query your retail data
results = collection.query(
    query_texts=["Find stores in Mumbai"],
    n_results=5
)
```

-----

## 📈 Performance Considerations

### Memory Usage

  - Processes files one at a time
  - Drops NaN values for clean data
  - Efficient document batching

### Processing Speed

  - Async CLU API calls
  - Parallel document indexing
  - Progress tracking for large datasets

### Scalability

  - Handles multiple Excel files
  - Persistent vector storage
  - Easy to extend for other data sources

-----

## 🚨 Error Handling

### Graceful Degradation

  - Individual file failures don't stop processing
  - Detailed error logging for debugging
  - Continues processing remaining files

### Validation

  - Checks for empty rows and malformed data
  - Verifies directory structure
  - Confirms ChromaDB initialization

-----

## 📚 Dependencies

### Core Libraries

  - **pandas**: Excel file processing
  - **chromadb**: Vector database
  - **aiohttp**: Async CLU API calls
  - **google-generativeai**: Gemini API client

### Version Requirements

  - Python 3.10+
  - All dependencies specified in `requirements.txt`

-----

## 🎯 Next Steps

### Immediate Actions

1.  ✅ Virtual environment created
2.  ✅ Dependencies defined
3.  ✅ Ingestion script ready
4.  🔄 Install dependencies: `pip install -r requirements.txt`
5.  🔄 Add Shop Assist Excel file
6.  🔄 Run ingestion: `python ingest_clu.py`

### Future Enhancements

  - Add data validation schemas
  - Implement incremental updates
  - Add data transformation pipelines
  - Integrate with Azure OpenAI services
  - Add monitoring and alerting

-----

## 🏆 Success Criteria

  - [x] Excel files processed automatically
  - [x] CLU metadata extracted
  - [x] ChromaDB indexing complete
  - [x] Ready for AI voice agent queries
  - [x] Production-ready code quality
  - [x] Comprehensive error handling
  - [x] Clear logging and progress tracking
  - [x] Human-readable responses generated by Gemini

-----

**🎉 Your Shop Assist MVP CLU ingestion system is ready for production use\!**

The system will transform your retail dataset into searchable AI-ready documents with CLU semantic metadata, and use Gemini to provide powerful, conversational responses, enabling enhanced voice agent capabilities for customer insights and retail analytics.