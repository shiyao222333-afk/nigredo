"""
⚗️ Nigredo — 熔知联动桥接

将 Nigredo 的产出注入 Citrinitas 知识库。
独立项目通过标准 JSON 接口通信。
"""
import requests
from config import QDRANT_URL, QDRANT_COLLECTION_VIDEO, QDRANT_COLLECTION_ANALYSIS


def inject_to_athanor(
    content: str,
    collection: str = None,
    metadata: dict = None,
) -> bool:
    """
    将文档注入 Citrinitas 知识库。

    通过 Qdrant HTTP API 直接写入（不依赖 Citrinitas 代码）。
    """
    collection = collection or QDRANT_COLLECTION_VIDEO

    try:
        # 生成嵌入向量（用简单的文本 hash 兜底，实际用 Ollama embedding）
        embedding = _generate_embedding(content)

        payload = {
            "points": [{
                "id": metadata.get("id") if metadata else 0,
                "vector": embedding,
                "payload": {
                    "text": content,
                    **(metadata or {}),
                    "source": "alembic",
                    "pipeline": "video-forge",
                },
            }]
        }

        resp = requests.put(
            f"{QDRANT_URL}/collections/{collection}/points",
            json=payload,
            timeout=30,
        )
        return resp.status_code == 200
    except Exception:
        return False


def _generate_embedding(text: str, dim: int = 1024) -> list[float]:
    """
    生成文本嵌入向量。

    优先调用 Ollama embedding API。
    """
    try:
        resp = requests.post(
            "http://localhost:11434/api/embeddings",
            json={"model": "bge-m3", "prompt": text[:8192]},
            timeout=30,
        )
        data = resp.json()
        return data.get("embedding", [])
    except Exception:
        # 回退：简单哈希兜底（not for production）
        import hashlib
        hash_bytes = hashlib.sha256(text.encode()).digest()
        return [(b / 255.0) for b in hash_bytes[:dim]]
