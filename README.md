# MoSPI Crawler + RAG

An end-to-end web scraper and retrieval-augmented generation (RAG) app for MoSPI press releases. It discovers press-release PDF links, downloads and parses content, extracts one table, stores metadata in SQLite, and indexes text to a local Chroma vector store. A Streamlit UI lets you trigger scraping, view progress, ask questions, and inspect stored data.

##Demo

https://www.youtube.com/watch?v=PwUhBPHbGqo

## Architecture

### Components
- `scraper/`
  - `crawl.py`: Listing discovery with pagination and strict URL filter to `https://www.mospi.gov.in/sites/default/files/press_release/*.pdf`; optional detail metadata; uses polite HTTP utilities.
  - `http.py`: Requests session with retries, backoff, rate limiting, and configurable robots.txt respect.
  - `parse.py`: Text extraction via `pdfplumber` (OCR fallback optional) and first-table extraction.
  - `models.py`: SQLite schema + helpers for `documents`, `files`, and `tables`.
  - `config.py`: Env-driven configuration (timeouts, retries, rate limits, pagination caps, user-agent, robots flag).
- `pipeline/run.py`: Orchestrates discovery → DB upserts → download → parse text/table → write processed `.txt` → index text → mark processed. Emits structured logs.
- `rag/`
  - `retriever.py`: Initializes persistent Chroma at `data/chroma_db`; chunks and indexes text and calls `persist()`.
  - `api.py`: Retrieves relevant chunks and queries the LLM with a prompt template.
- `rag/ui/`
  - `app.py`: Streamlit UI to run the pipeline with progress messages (current URL/file) and ask questions.
  - `database_viewer.py`: Streamlit viewer for DB tables with an Excel export option.

### Data flow
1. User provides a seed URL in the UI.
2. `scrape_listing_and_details()` finds press-release PDFs via pagination.
3. `documents` and `files` upserted into SQLite (`data/mospi.db`).
4. PDFs are downloaded to `data/raw/`.
5. Text and first table are extracted. Text is saved to `data/processed/<pdf_name>.txt`.
6. Text is chunked and indexed to Chroma (`data/chroma_db`).
7. Q&A: UI queries retrieve similar chunks; LLM answers using the prompt template.

### Storage schema (SQLite)
- `documents(id, title, url, date_published, summary, category, doc_hash, created_at)`
- `files(id, document_id, file_url, file_path, file_hash, file_type, pages, downloaded, processed, created_at)`
- `tables(id, document_id, source_file_id, table_json, n_rows, n_cols, created_at)`

## Trade-offs
- **SQLite**: Simple and portable for single-user/container. For multi-user/concurrent writes, Postgres is more robust.
- **pdfplumber vs Camelot/Tabula**: `pdfplumber` is light and Python-native; Camelot/Tabula can extract more complex tables but add heavier dependencies (Java/Ghostscript) and container size.
- **Streamlit**: Fast to build UX with simple state handling, but not ideal for background jobs or multi-user auth. A backend service (FastAPI + worker) would scale better.
- **Local Chroma**: Zero-ops and persistent on disk. For distributed setups, consider a remote vector DB or Chroma server.
- **Heuristic scraping**: Robust against minor structure changes but not foolproof. Site-specific selectors would increase reliability.

## Future improvements
- Crawler robustness: site-specific selectors, pagination detection improvements, and snapshot tests.
- Versioning and dedup: compare normalized content hashes to detect updates and keep versions.
- Table extraction: plug-in Camelot/Tabula with runtime selection; store table locations/pages.
- Metadata enrichment: better date parsing, category mapping, and summaries from details or PDF metadata.
- RAG quality: reranking, chunking/overlap tuning, prompt improvements, response grounding and citations, evaluation (e.g., RAGAS).
- Background jobs: move pipeline to a task queue (Celery/RQ) and stream progress to UI.
- API surface: optional FastAPI endpoints for scrape, status, and Q&A.
- Observability: structured logs shipping, metrics, alerts.

## Local quickstart
```bash
# (optional) venv
python -m venv .venv && . .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -r requirements.txt
streamlit run rag/ui/app.py
```

## Docker quickstart
Build and run with Docker directly:
```bash
# Build
docker build -t mospi-app .

# Run (Windows PowerShell example; adjust path mount for your OS)
docker run --rm -it -p 8501:8501 -v ${PWD}/data:/app/data mospi-app
```

Using docker-compose (includes database viewer on port 8502):
```bash
docker compose up --build
```
- App: http://localhost:8501
- DB Viewer: http://localhost:8502

### Environment configuration
Override via docker-compose or `-e` flags:
- `SCRAPER_MAX_PAGES_PER_SEED` (default 3–5)
- `SCRAPER_RESPECT_ROBOTS` (default false)
- `SCRAPER_RATE_LIMIT_SECONDS` (default 0.5)
- `SCRAPER_USER_AGENT`

Data is persisted in `data/`.
