# Shop Assist RAG Project

This is the main repository for the Shop Assist RAG (Retrieval-Augmented Generation) application.

## Project Structure

```
rag/
├── ragApp/              # Main application folder (all runtime files)
│   ├── app_flask.py    # Flask application entry point
│   ├── static/         # CSS and JavaScript files
│   ├── templates/      # HTML templates
│   ├── data/           # Data files and images
│   ├── chroma_db/      # ChromaDB database
│   └── ...             # Other application files
│
├── documents/          # All documentation files (.md)
│   ├── README.md       # Documentation index
│   ├── QUICKSTART.md   # Quick start guide
│   └── ...             # Other documentation
│
├── venv/               # Python virtual environment (excluded from git)
└── README.md          # This file

```

## Quick Start

1. Navigate to the application folder:
   ```bash
   cd ragApp
   ```

2. Create virtual environment
   ```bash
   python -m venv venv
   ```   

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements_flask.txt
   ```

4. Configure the application:
   - Edit `ragApp/config.yaml` with your settings

5. Run the application:
   ```bash
   python app_flask.py
   ```

6. Access the application:
   - Open your browser to `http://localhost:5000`

## Documentation

All documentation files are located in the `documents/` folder. See `documents/README.md` for a complete list.

## Application Files

All application files required to run the project are in the `ragApp/` folder. See `ragApp/README.md` for details.

## Notes

- The `venv/` folder contains the Python virtual environment and should not be committed to version control
- The `__pycache__/` folders are Python cache directories and can be ignored
- All markdown documentation files have been moved to the `documents/` folder
