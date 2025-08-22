import pdfplumber
import streamlit as st
from typing import List

def extract_text_from_pdf(file_path: str, ocr: bool = False) -> str:
    text_parts = []
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                txt = page.extract_text() or ""
                if txt:
                    text_parts.append(txt)
    except Exception as e:
        st.error(f"Failed to read {file_path} → {e}")

    text = "\n\n".join(text_parts)

    if ocr and not text.strip():
        try:
            from pdf2image import convert_from_path
            import pytesseract
            images = convert_from_path(file_path, dpi=300)
            text = "\n".join(pytesseract.image_to_string(img) for img in images)
        except Exception as e:
            st.error(f"OCR failed for {file_path}: {e}")
    return text


def extract_first_table(file_path: str) -> list[list[str]]:
    """Extract the first table found using pdfplumber; returns rows of strings.
    Falls back to empty list if none found.
    """
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables() or []
                if not tables:
                    continue
                # Take the first table
                raw_rows = tables[0]
                # Normalize cells to strings
                rows: List[List[str]] = []
                for r in raw_rows:
                    rows.append([(c if c is not None else "").strip() for c in r])
                return rows
    except Exception as e:
        st.error(f"Table extract failed for {file_path}: {e}")
    return []
