from scraper.crawl import scrape_pdf_links, download_pdf_to_disk, scrape_listing_and_details
from scraper.parse import extract_text_from_pdf, extract_first_table
from scraper.models import (
    init_db, upsert_file_url, get_unprocessed, update_after_download, mark_processed,
    upsert_document, upsert_file_for_document, set_file_meta, insert_table, update_file_path,
)
from scraper import logging as log
import os, shutil
from rag.retriever import chunk_and_index

def run_pipeline(base_url: str, limit=2, use_ocr=False):
    init_db()
    # Discover documents + files
    docs = scrape_listing_and_details(base_url)
    log.info("discovered_docs", count=len(docs))
    for d in docs:
        doc_id = upsert_document(
            url=d.get("url"),
            title=d.get("title"),
            date_published=d.get("date_published"),
            summary=d.get("summary"),
            category=d.get("category"),
        )
        for f_url in d.get("file_links", [])[: limit]:
            file_id = upsert_file_for_document(doc_id, f_url)
            upsert_file_url(f_url)

    # Process unprocessed files
    rows = get_unprocessed(limit=limit)
    for file_id, file_url, file_path, downloaded, processed in rows:
        try:
            if not downloaded:
                path, file_hash = download_pdf_to_disk(file_url)
                update_after_download(file_id, path, file_hash)
                file_path = path
            text = extract_text_from_pdf(file_path, ocr=use_ocr)
            # set metadata: pages
            try:
                import pdfplumber
                with pdfplumber.open(file_path) as pdf:
                    set_file_meta(file_id, file_type="pdf", pages=len(pdf.pages))
            except Exception:
                set_file_meta(file_id, file_type="pdf", pages=None)
            # table extraction
            table = extract_first_table(file_path)
            if table:
                # We do not have document_id in this row; fetch it
                # Simple query: get doc_id via helper
                from sqlite3 import connect
                conn = connect("data/mospi.db")
                cur = conn.cursor()
                cur.execute("SELECT document_id FROM files WHERE id=?", (file_id,))
                row = cur.fetchone()
                doc_id = row[0] if row else None
                conn.close()
                if doc_id:
                    insert_table(doc_id, file_id, table)
            # Save extracted text to data/processed as .txt (PDF remains in data/raw)
            try:
                processed_dir = os.path.join("data", "processed")
                os.makedirs(processed_dir, exist_ok=True)
                base = os.path.splitext(os.path.basename(file_path))[0]
                txt_path = os.path.join(processed_dir, base + ".txt")
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(text)
            except Exception as e:
                log.error("write_text_failed", file_path=file_path, error=str(e))
                txt_path = file_path

            # index text (use txt path as source if available)
            chunk_and_index(text, meta_source=txt_path)
            mark_processed(file_id)
            log.info("file_processed", file_url=file_url, file_path=file_path)
        except Exception as e:
            log.error("file_process_failed", file_url=file_url, error=str(e))
