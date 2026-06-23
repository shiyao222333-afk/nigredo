"""
⚗️ Nigredo — 缓存/去重管理器
"""
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta


class VideoCache:
    """基于 BV号 的去重缓存"""

    def __init__(self, cache_dir: Path):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.cache_dir / "index.json"
        self._index = self._load_index()

    def is_processed(self, video_id: str) -> bool:
        return video_id in self._index

    def mark_processed(self, video_id: str, metadata: dict = None):
        tz = timezone(timedelta(hours=8))
        self._index[video_id] = {
            "processed_at": datetime.now(tz).isoformat(),
            "metadata": metadata or {},
        }
        self._save_index()

    def get_metadata(self, video_id: str) -> dict:
        return self._index.get(video_id, {}).get("metadata", {})

    def _load_index(self) -> dict:
        if self.index_file.exists():
            try:
                return json.loads(self.index_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _save_index(self):
        self.index_file.write_text(
            json.dumps(self._index, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
