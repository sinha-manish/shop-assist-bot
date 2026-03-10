# Deployment Setup Guide

## ChromaDB Collection Issue

The application requires a ChromaDB collection with ingested data. The `chroma_db/` directory is excluded from the Docker image to keep it small.

## Solutions

### Option 1: Mount ChromaDB as Volume (Recommended for Production)

If you have the `chroma_db/` directory locally, mount it as a volume:

```bash
docker run -p 5000:5000 \
  -v $(pwd)/chroma_db:/app/chroma_db \
  chatbot-app:latest
```

For Azure App Service, configure a persistent storage mount for `/app/chroma_db`.

### Option 2: Include ChromaDB in Image (For Testing)

If the `chroma_db/` is small enough, you can include it:

1. Remove `chroma_db/` from `.dockerignore`
2. Rebuild the image

**Note**: This will increase image size significantly if you have a large database.

### Option 3: Run Ingestion After Deployment

If the collection doesn't exist, the app will create an empty one and start. You can then:

1. Copy the Excel file into the container:
   ```bash
   docker cp data/documents/shop_assist_hyderabad.xlsx <container_id>:/app/data/documents/
   ```

2. Run ingestion inside the container:
   ```bash
   docker exec <container_id> python ingest_clu.py
   ```

**Note**: This requires `ingest_clu.py` to be in the image (currently excluded).

### Option 4: Pre-populate Before Deployment

1. Run ingestion locally to create `chroma_db/`
2. Mount it as volume (Option 1)

## Current Status

The code has been updated to:
- ✅ Create an empty collection if it doesn't exist (app won't crash)
- ✅ Show warning messages about empty/missing collection
- ✅ Allow app to start even without data (but search won't work)

## Azure App Service Setup

For Azure App Service, you need to:

1. **Mount Persistent Storage**:
   - Configure Azure File Share or Blob Storage
   - Mount to `/app/chroma_db` path

2. **Or Use Azure Container Instances with Volumes**:
   - Use Azure Files for persistent storage
   - Mount the volume during container creation

## Verification

After deployment, check logs for:
- `✓ Collection exists with X documents` - Good!
- `⚠️ Collection exists but is empty` - Need to run ingestion
- `⚠️ Collection does not exist. Creating empty collection.` - Need to populate data

## Quick Fix for Testing

If you just need to test the app quickly:

1. **Include ingestion script in image** (modify `.dockerignore`):
   ```
   # Remove this line:
   ingest_clu.py
   ```

2. **Include Excel file** (modify `.dockerignore`):
   ```
   # Remove or comment:
   # *.xlsx
   ```

3. **Include chroma_db** (modify `.dockerignore`):
   ```
   # Remove or comment:
   # chroma_db/
   ```

4. Rebuild and the app will have everything it needs.

**Warning**: This will significantly increase image size!

