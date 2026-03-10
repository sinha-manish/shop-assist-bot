### 🚀 Get Started in 3 Steps

#### **Option 1: Python Virtual Environment** 🐍

This is the recommended method for local development to isolate project dependencies.

1.  **Create and Activate Environment**

    ```bash
    # Create the virtual environment
    python -m venv venv

    # Activate it on Windows
    .\venv\Scripts\activate

    # Activate it on macOS/Linux
    source venv/bin/activate
    ```

2.  **Install Dependencies**

    ```bash
    pip install -r requirements.txt
    ```

    This command installs all necessary libraries, including `pandas`, `chromadb`, and `aiohttp`.

3.  **Configure CLU**
    Edit the `config.yaml` file with your specific Microsoft CLU endpoint, key, project, and deployment names.

4.  **Add Excel Files**
    Place your `.xlsx` files containing Shop Assist retail data into the `data/documents/` folder.

5.  **Run CLU Ingestion**

    ```bash
    python ingest_clu.py
    ```

    This script will process your data and build the vector database.

6.  **Run the Web Chat UI**

    ```bash
    python app.py
    ```

    This will launch the Flask web chat assistant at [http://localhost:5000](http://localhost:5000).

-----

#### **Option 2: Docker Containerization** 🐳

This is the best approach for a consistent, production-ready setup.

1.  **Build the Docker Image**

    ```bash
    docker build -t clu-ingestion .
    ```

    This command reads the `Dockerfile` to create an image containing all dependencies and your application code.

2.  **Configure CLU**
    Create a file named `.env` in the project root with your CLU credentials.

    ```env
    CLU_ENDPOINT="your_clu_endpoint"
    CLU_KEY="your_clu_key"
    CLU_PROJECT_NAME="your_project_name"
    CLU_DEPLOYMENT_NAME="your_deployment_name"
    ```

3.  **Add Excel Files**
    Ensure your `.xlsx` files are located in the `data/documents/` folder, as this directory will be mounted into the container.

4.  **Run the Ingestion Container**

    ```bash
    docker run --rm -it --env-file .env -v ./data:/app/data -v ./chroma_db:/app/chroma_db clu-ingestion python app.py
    ```

    This command runs the container, passes your environment variables, and maps the `data` and `chroma_db` directories so you can access the input and output files from your host machine.

-----

### 📁 What Gets Created

  - **`chroma_db/`**: This directory stores the persistent **ChromaDB vector database**. It contains all your CLU-analyzed documents, ready for fast retrieval.
  - **`data/documents/`**: A new `.json` file is created for each processed Excel file, serving as a structured export of the row data.
  - **Console Logs**: Detailed logs track the ingestion progress, document counts, and any errors encountered.

-----

### ❓ Need Help?

    - **Verify Setup**: Run `python app.py` (or `docker run ... python app.py`) to test the CLU, Gemini, and ChromaDB connections.
  - **Documentation**: Refer to the full `README.md` for in-depth technical details and troubleshooting.

-----

### 🎯 What Happens

1.  **Excel Processing**: The script reads each Excel row and transforms it into a searchable document string.
2.  **CLU Analysis**: The document strings are sent to the Microsoft CLU API. CLU's pre-trained model extracts **intent** (e.g., "FindApparel", "CheckInventory") and **entities** (e.g., "Product\_Category", "Size", "Store\_Location").
3.  **Vector Storage**: The documents, along with their CLU metadata, are converted into numerical vectors and stored in **ChromaDB**. This process creates a searchable index that can handle complex, natural language queries.
4.  **Metadata**: The original source file, row index, and CLU results are all stored as metadata, enabling powerful **hybrid search** (semantic + metadata filtering).

Your retail data is now fully optimized and ready to power sophisticated RAG applications with a modern Flask web chat UI and Gemini-powered responses. 🎉