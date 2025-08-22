import json, sys, time
from typing import Any, Dict


def log(level: str, message: str, **context: Dict[str, Any]):
	entry = {
		"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
		"level": level.lower(),
		"msg": message,
	}
	if context:
		entry.update(context)
	sys.stdout.write(json.dumps(entry, ensure_ascii=False) + "\n")
	sys.stdout.flush()


def info(message: str, **context):
	log("info", message, **context)


def warn(message: str, **context):
	log("warning", message, **context)


def error(message: str, **context):
	log("error", message, **context)
