import time, random
from urllib.parse import urlparse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from .config import USER_AGENT, REQUEST_TIMEOUT_SECONDS, MAX_RETRIES, BACKOFF_BASE_SECONDS, RATE_LIMIT_SECONDS, RESPECT_ROBOTS
from . import logging as log


_session = None
_last_request_time = 0.0
_robots_cache = {}


def _build_session() -> requests.Session:
	s = requests.Session()
	s.headers.update({"User-Agent": USER_AGENT})
	retry = Retry(
		total=MAX_RETRIES,
		backoff_factor=BACKOFF_BASE_SECONDS,
		status_forcelist=[429, 500, 502, 503, 504],
		allowed_methods=["GET", "HEAD"],
	)
	s.mount("http://", HTTPAdapter(max_retries=retry))
	s.mount("https://", HTTPAdapter(max_retries=retry))
	return s


def get_session() -> requests.Session:
	global _session
	if _session is None:
		_session = _build_session()
	return _session


def _rate_limit_wait():
	global _last_request_time
	delta = time.time() - _last_request_time
	to_sleep = RATE_LIMIT_SECONDS - delta
	if to_sleep > 0:
		time.sleep(to_sleep)
	_last_request_time = time.time()


def _is_allowed_by_robots(url: str) -> bool:
	if not RESPECT_ROBOTS:
		return True
	parsed = urlparse(url)
	root = f"{parsed.scheme}://{parsed.netloc}"
	if root not in _robots_cache:
		robots_url = root + "/robots.txt"
		try:
			resp = get_session().get(robots_url, timeout=REQUEST_TIMEOUT_SECONDS)
			text = resp.text.lower()
			_robots_cache[root] = "disallow: /" not in text
		except Exception:
			_robots_cache[root] = True
	return _robots_cache[root]


def http_get(url: str, **kwargs) -> requests.Response:
	if not _is_allowed_by_robots(url):
		raise RuntimeError(f"Blocked by robots.txt: {url}")
	_rate_limit_wait()
	try:
		resp = get_session().get(url, timeout=REQUEST_TIMEOUT_SECONDS, **kwargs)
		resp.raise_for_status()
		return resp
	except Exception as e:
		log.error("http_get_failed", url=url, error=str(e))
		raise
