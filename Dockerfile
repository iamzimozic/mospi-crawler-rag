# syntax=docker/dockerfile:1
FROM python:3.11-slim

# System deps for pdf2image/poppler and tesseract (optional OCR)
RUN apt-get update && apt-get install -y --no-install-recommends \
	build-essential \
	poppler-utils \
	tesseract-ocr \
	libgl1 \
	curl \
	&& rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install python deps first (cache)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY . .

# Create data directories
RUN mkdir -p data/raw data/processed data/chroma_db

# Expose Streamlit port
EXPOSE 8501

# Environment configuration defaults
ENV SCRAPER_USER_AGENT="MoSPI-Scraper/1.0 (Docker)" \
	SCRAPER_MAX_PAGES_PER_SEED=3 \
	SCRAPER_RESPECT_ROBOTS=false

# Streamlit settings
ENV STREAMLIT_SERVER_PORT=8501 \
	STREAMLIT_SERVER_HEADLESS=true

# Run the main Streamlit UI
CMD ["streamlit", "run", "rag/ui/app.py"]
