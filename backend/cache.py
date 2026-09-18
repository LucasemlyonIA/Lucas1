"""Cache disque simple (fichier JSON) avec TTL pour éviter de spammer l'API Retail Prices."""
from __future__ import annotations

import json
import time
from pathlib import Path
from threading import Lock
from typing import Any, Optional

CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"
CACHE_FILE = CACHE_DIR / "prices_cache.json"
DEFAULT_TTL_SECONDS = 24 * 60 * 60  # 24h


class PriceCache:
    def __init__(self, path: Path = CACHE_FILE, ttl_seconds: int = DEFAULT_TTL_SECONDS):
        self.path = path
        self.ttl_seconds = ttl_seconds
        self._lock = Lock()
        self._data: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._data = {}
        else:
            self._data = {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, ensure_ascii=False), encoding="utf-8")

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._data.get(key)
            if not entry:
                return None
            if time.time() - entry["timestamp"] > self.ttl_seconds:
                return None
            return entry["value"]

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._data[key] = {"timestamp": time.time(), "value": value}
            self._save()

    def clear(self) -> None:
        with self._lock:
            self._data = {}
            self._save()


price_cache = PriceCache()
