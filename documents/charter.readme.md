### 🗺️ Shop Assist RAG System - Architecture Charter & Dependencies (Gemini & CLU Version)

## 📋 **Project Overview**

**Project**: AI-Powered Voice Agent for Enhanced Customer Insights in Retail
**Architecture**: Retrieval-Augmented Generation (RAG) System with Multi-Modal Interfaces, CLU, and Gemini Integration
**Core Purpose**: Convert retail data into searchable vector documents with CLU semantic metadata to power an AI voice agent and other interfaces, using Gemini to generate human-readable, conversational responses from structured data.

-----

## 🏗️ **System Architecture Overview**

The system is a classic **RAG architecture** with three distinct layers, now enhanced with a Large Language Model (LLM) for content generation.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            DATA LAYER                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│   Raw Data: advanced_shop_assist_store_data.xlsx                           │
│   Ingestion Script: ingest_clu.py                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CORE RAG LAYER                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│   Conversational Language Understanding (CLU) API: Intent/Entities Extraction│
│   Gemini API: Natural Language Generation                                   │
│   ChromaDB Vector Store: shop_assist_retail_data_clu                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        INTERFACE LAYER                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│   Flask Web UI: Modern chat interface for all users.                        │
│   - Generates final conversational responses using Gemini.                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

-----

## 📊 **File Dependencies Matrix**

### **Core Functionality**

| File | Purpose | Dependencies | Input | Output | Used By |
|---|---|---|---|---|---|
| `create_advanced_store_data.py` | Generates rich, mock retail data into an Excel file. | `pandas`, `numpy`, `random` | N/A | `advanced_shop_assist_store_data.xlsx` | `ingest_clu.py` |
| `ingest_clu.py` | **CORE INGESTION SCRIPT**. Reads the Excel data, uses CLU to get embeddings and metadata, then populates ChromaDB. | `chromadb`, `aiohttp`, `CLU API` | `*.xlsx` | ChromaDB collection | **All UI Files** |
| `demo_queries.py` | Demonstrates basic query capabilities from the command line. | `chromadb` | ChromaDB | Console | N/A |
| `interactive_query.py` | Provides a simple interactive command-line interface for querying. | `chromadb` | ChromaDB | Console | N/A |
| `app.py` | Contains the `generate_human_readable_response` function that calls the Gemini API. | `google.generativeai` | Structured data from search | Human-readable text | UI Files |

### **User Interface Files**

| File | Purpose | Dependencies | Data Source | Port |
|---|---|---|---|---|
| `web_ui.py` | Basic text-based web UI. **Now uses Gemini for response generation.** | `gradio`, `chromadb`, `google.generativeai` | ChromaDB | **7860** |
| `smart_consumer_ui.py` | **MAIN UI**. Hybrid text + voice interface for consumers. **Now uses Gemini for response generation.** | `gradio`, `chromadb`, `speech_recognition`, `pyttsx3`, `google.generativeai` | ChromaDB | **7861** |
| `voice_chat_advanced.py` | Advanced voice-only interface using the Whisper model. **Now uses Gemini for response generation.** | `gradio`, `chromadb`, `whisper`, `google.generativeai` | ChromaDB | **7864** |
| `store_smart_assistant.py` | UI designed for store management tasks. **Now uses Gemini for response generation.** | `gradio`, `chromadb`, `google.generativeai` | ChromaDB | **7865** |
| `store_web_interface.py` | Alternative text UI for stores. **Now uses Gemini for response generation.** | `gradio`, `chromadb`, `google.generativeai` | ChromaDB | **7860** |
| `store_consumer_ui.py` | Alternative text UI for store consumers. **Now uses Gemini for response generation.** | `gradio`, `chromadb`, `google.generativeai` | ChromaDB | **7862** |
| `dual_mode_ui.py` | Combines text and basic voice features. **Now uses Gemini for response generation.** | `gradio`, `chromadb`, `speech_recognition`, `pyttsx3`, `google.generativeai` | ChromaDB | **7861** |

-----

## 🤖 **AI Models & Library Dependencies**

### **Core AI Models**

| Model | Type | Purpose | Used In | Configuration |
|---|---|---|---|---|
| **`CLU API`** | Conversational Language Understanding | **Intent and Entity Extraction** | `ingest_clu.py`, `smart_consumer_ui.py`, `voice_chat_advanced.py`, etc. | `config.yaml` |
| **`Gemini API`** | Large Language Model (LLM) | **Conversational Response Generation** | All UI files (`web_ui.py`, `smart_consumer_ui.py`, etc.) | `os.getenv("GOOGLE_API_KEY")` |
| **`whisper/base`** | Speech-to-Text | Transcribes spoken queries into text. | `voice_chat_advanced.py` | Base model |
| **`pyttsx3`** | Text-to-Speech | Converts text output to speech. | `smart_consumer_ui.py`, `dual_mode_ui.py` | Offline TTS |

### **Library Dependencies by Category**

  * **Core RAG Libraries**
      * `chromadb>=0.4.0`: The primary **vector database**.
      * `aiohttp>=3.8.0`: Enables **asynchronous CLU API calls** during ingestion.
      * `google-generativeai`: The **Gemini API client** for response generation.
  * **Data Processing Libraries**
      * `pandas>=2.0.0`: Essential for reading and manipulating **Excel files**.
      * `openpyxl>=3.1.0`: Supports reading `.xlsx` files.
  * **UI Framework Libraries**
      * `gradio>=4.0.0`: The framework used to create all **web interfaces**.
  * **Audio Processing Libraries**
      * `speechrecognition>=3.10.0`: Handles voice input.
      * `pyttsx3>=2.90`: Provides a simple TTS engine.
      * `whisper`: An advanced **Speech-to-Text** model.

-----

## 🔄 **Data & Query Flow**

### **1. Data Flow: From Excel to ChromaDB**

`Excel File (.xlsx) ➡️ ingest_clu.py (pandas) ➡️ CLU API (analysis) ➡️ ChromaDB (storage)`

### **2. Query Flow: From UI to Results**

`User Query (Text/Voice) ➡️ UI File ➡️ CLU API (intent/entities) ➡️ ChromaDB (search & filter) ➡️ Structured Data ➡️ Gemini API (response generation) ➡️ Final Response (formatted in HTML/Audio)`

-----

## 🚀 **Deployment & Troubleshooting**

### **Standard Startup Sequence**

1.  **Activate Virtual Environment**: `.\venv\Scripts\Activate.ps1`
2.  **Set API Keys**: Set your environment variables for both CLU and Gemini: `set GOOGLE_API_KEY=your_key_here` and the CLU keys from `config.yaml`.
3.  **Generate Data (if needed)**: `python create_advanced_store_data.py`
4.  **Ingest Data**: `python ingest_clu.py` (This is a **critical** one-time step for fresh data).
5.  **Launch Interface**: `python <desired_ui_file.py>`

### **Common Issues & Solutions**

  * **Missing Module**: `ModuleNotFoundError: ...`
      * **Cause**: The required library isn't installed in your environment.
      * **Solution**: Run `pip install -r requirements.txt`.
  * **Port In Use**: `Address already in use`
      * **Cause**: You are trying to run two UI files on the same port (e.g., `web_ui.py` and `store_web_interface.py` both use 7860).
      * **Solution**: Close the first script or run the second one on a different port.
  * **No Search Results**: The system can't find products.
      * **Cause**: ChromaDB is empty or the collection wasn't created.
      * **Solution**: Ensure `ingest_clu.py` has been run successfully and the `chroma_db` folder exists with data.
  * **Gemini API Error**: `google.api_core.exceptions.InvalidArgument: 400 Request contains an invalid argument.`
      * **Cause**: The Gemini API key is incorrect or not set.
      * **Solution**: Double-check that the `GOOGLE_API_KEY` environment variable is set correctly and the key is valid.