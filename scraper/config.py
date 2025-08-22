import os


def get_bool(name: str, default: bool) -> bool:
	v = os.getenv(name)
	if v is None:
		return default
	return v.strip().lower() in {"1", "true", "yes", "y", "on"}


def get_int(name: str, default: int) -> int:
	try:
		return int(os.getenv(name, str(default)))
	except Exception:
		return default


def get_float(name: str, default: float) -> float:
	try:
		return float(os.getenv(name, str(default)))
	except Exception:
		return default


USER_AGENT = os.getenv("SCRAPER_USER_AGENT", "MoSPI-Scraper/1.0 (+contact: example@example.com)")
REQUEST_TIMEOUT_SECONDS = get_int("SCRAPER_REQUEST_TIMEOUT_SECONDS", 30)
MAX_RETRIES = get_int("SCRAPER_MAX_RETRIES", 3)
BACKOFF_BASE_SECONDS = get_float("SCRAPER_BACKOFF_BASE_SECONDS", 1.0)
RATE_LIMIT_SECONDS = get_float("SCRAPER_RATE_LIMIT_SECONDS", 0.5)
RESPECT_ROBOTS = get_bool("SCRAPER_RESPECT_ROBOTS", False)
MAX_PAGES_PER_SEED = get_int("SCRAPER_MAX_PAGES_PER_SEED", 5)
CONCURRENCY = get_int("SCRAPER_CONCURRENCY", 1)  # placeholder for future use
