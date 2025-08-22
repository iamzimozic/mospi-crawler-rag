import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


import streamlit as st
from pipeline.run import run_pipeline
from rag.api import retrieve_and_answer
from scraper import logging as log

st.set_page_config(page_title="MoSPI AI Crawler + RAG", page_icon="📄")
st.title("MoSPI AI Crawler + RAG")

url = st.text_input("Enter MoSPI Press Release URL")
use_ocr = st.toggle("🔎 Use OCR fallback for scanned PDFs", value=False)

col_a, col_b = st.columns(2)
with col_a:
    if st.button("Scrape & Process PDFs"):
        if url.strip():
            # Create a status container to show progress
            status_container = st.empty()
            status_container.info("Starting pipeline...")
            
            try:
                # Override the logger to also show in Streamlit
                original_log = log.info
                def streamlit_log(message, **context):
                    original_log(message, **context)
                    if "url" in context:
                        status_container.info(f"Processing: {context['url']}")
                    elif "file_url" in context:
                        status_container.info(f"Processing file: {context['file_url']}")
                    elif "file_path" in context:
                        status_container.info(f"Processing file: {context['file_path']}")
                    elif "count" in context:
                        status_container.info(f"Discovered {context['count']} documents")
                
                # Temporarily replace the logger
                log.info = streamlit_log
                
                run_pipeline(url, use_ocr=use_ocr)
                
                # Restore original logger
                log.info = original_log
                
                status_container.success("Processed PDFs successfully.")
            except Exception as e:
                status_container.error(f"Error: {str(e)}")
        else:
            st.warning("Please enter a URL.")

st.subheader("Ask Questions")
q = st.chat_input("Type your question…")
if q:
    st.chat_message("user").write(q)
    ans = retrieve_and_answer(q)
    st.chat_message("assistant").write(ans)
