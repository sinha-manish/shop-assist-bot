# ----------------------------
# Base Image
# ----------------------------
FROM python:3.11-slim

# ----------------------------
# Environment Variables
# ----------------------------
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Disable telemetry for ChromaDB, Chroma, LangChain, Gemini
ENV CHROMADB_TELEMETRY_DISABLED=true
ENV CHROMA_TELEMETRY_DISABLED=true
ENV LANGCHAIN_TELEMETRY=false
ENV GOOGLE_GENAI_TELEMETRY_DISABLED=true

# Azure App Service port
ENV PORT=5000

# ----------------------------
# Set Working Directory
# ----------------------------
WORKDIR /app

# ----------------------------
# Install Dependencies
# ----------------------------
COPY requirements.txt .

RUN pip install --upgrade pip \
    && pip install numpy==1.26.1 \
    && pip install -r requirements.txt

# ----------------------------
# Copy Application Code
# ----------------------------
COPY . .

# ----------------------------
# Expose Port
# ----------------------------
EXPOSE 5000

# ----------------------------
# Start the Application
# ----------------------------
CMD ["python", "app_flask.py"]
