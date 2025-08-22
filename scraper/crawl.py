import os, re, hashlib
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from .http import http_get
from .models import compute_hash, sanitize_filename
from . import logging as log
from .config import MAX_PAGES_PER_SEED
import datetime

PDF_DIR = "data/raw"
os.makedirs(PDF_DIR, exist_ok=True)

def scrape_pdf_links(base_url: str) -> list[str]:
    """Discover PDF links from paginated listing pages.
    Follows pagination via anchors containing 'Next' up to MAX_PAGES_PER_SEED.
    """
    seen_pages = set()
    to_visit = [base_url]
    pdf_urls = []
    pages_visited = 0

    while to_visit and pages_visited < MAX_PAGES_PER_SEED:
        url = to_visit.pop(0)
        if url in seen_pages:
            continue
        seen_pages.add(url)
        try:
            resp = http_get(url)
        except Exception as e:
            log.error("listing_fetch_failed", url=url, error=str(e))
            continue
        soup = BeautifulSoup(resp.text, "html.parser")

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if re.search(r"https://www\.mospi\.gov\.in/sites/default/files/press_release/.*\.pdf", href, re.IGNORECASE):
                pdf_urls.append(urljoin(url, href))

        # Find next page link heuristically
        next_link = None
        for a in soup.find_all("a", href=True):
            label = (a.get_text() or "").strip().lower()
            if label in {"next", "next ›", "›", "older", ">>"}:
                next_link = urljoin(url, a["href"].strip())
                break
        if next_link:
            to_visit.append(next_link)
        pages_visited += 1

    # de-duplicate while preserving order
    return list(dict.fromkeys(pdf_urls))


def _normalize_date(text: str) -> str | None:
    if not text:
        return None
    # Try common date formats in MoSPI content like '20 June 2025' or '20-06-2025'
    candidates = [
        "%d %B %Y",
        "%d %b %Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
    ]
    for fmt in candidates:
        try:
            dt = datetime.datetime.strptime(text.strip(), fmt)
            return dt.date().isoformat()
        except Exception:
            continue
    return None


def _absolute(base: str, href: str) -> str:
    try:
        return urljoin(base, href)
    except Exception:
        return href


def scrape_listing_and_details(base_url: str) -> list[dict]:
    """Return a list of document dicts with metadata and file_links.
    Document: {url, title, date_published, summary, category, file_links}
    """
    docs: list[dict] = []
    seen_pages = set()
    to_visit = [base_url]
    pages_visited = 0

    while to_visit and pages_visited < MAX_PAGES_PER_SEED:
        url = to_visit.pop(0)
        if url in seen_pages:
            continue
        seen_pages.add(url)
        try:
            resp = http_get(url)
        except Exception as e:
            log.error("listing_fetch_failed", url=url, error=str(e))
            continue
        soup = BeautifulSoup(resp.text, "html.parser")

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href:
                continue
            if re.search(r"https://www\.mospi\.gov\.in/sites/default/files/press_release/.*\.pdf", href, re.IGNORECASE):
                pdf_url = _absolute(url, href)
                title = (a.get_text() or "").strip() or os.path.basename(pdf_url)
                # Try to find a nearby date
                date_text = None
                parent_text = (a.find_parent().get_text(" ", strip=True) if a.find_parent() else "")
                m = re.search(r"(\d{1,2}[\-/ ](?:[A-Za-z]{3,9}|\d{1,2})[\-/ ]\d{4})", parent_text)
                if m:
                    date_text = m.group(1)
                doc = {
                    "url": url,
                    "title": title,
                    "date_published": _normalize_date(date_text) or None,
                    "summary": None,
                    "category": "press_release",
                    "file_links": [pdf_url],
                }
                docs.append(doc)

        # pagination
        next_link = None
        for a in soup.find_all("a", href=True):
            label = (a.get_text() or "").strip().lower()
            if label in {"next", "next ›", "›", "older", ">>"}:
                next_link = _absolute(url, a["href"].strip())
                break
        if next_link:
            to_visit.append(next_link)
        pages_visited += 1

    # de-duplicate by (title, first file link)
    seen = set()
    unique_docs = []
    for d in docs:
        key = (d["title"], d["file_links"][0] if d["file_links"] else "")
        if key in seen:
            continue
        seen.add(key)
        unique_docs.append(d)
    return unique_docs

def download_pdf_to_disk(file_url: str):
    tail = file_url.rstrip("/").split("/")[-1] or hashlib.md5(file_url.encode()).hexdigest() + ".pdf"
    filename = sanitize_filename(tail)
    file_path = os.path.join(PDF_DIR, filename)

    if os.path.exists(file_path):
        return file_path, compute_hash(file_path)

    with http_get(file_url, stream=True) as r:
        with open(file_path, "wb") as f:
            for chunk in r.iter_content(8192):
                if chunk:
                    f.write(chunk)
    return file_path, compute_hash(file_path)
