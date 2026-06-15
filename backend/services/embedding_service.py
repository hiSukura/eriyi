"""
向量嵌入服务 —— 语义搜索核心
"""
import os
import time
import logging
from pathlib import Path

import numpy as np

from database import get_db, rows_to_dicts
from config import DATA_DIR

logger = logging.getLogger("eriyi.embedding")

_EMBEDDING_DIM = 384
_EMBEDDING_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
_model = None


# ─── 模型管理 ───

def _load_model():
    global _model
    if _model is not None:
        return _model
    try:
        from sentence_transformers import SentenceTransformer
        os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
        t = time.time()
        _model = SentenceTransformer(_EMBEDDING_MODEL_NAME)
        dim = _model.get_embedding_dimension() if hasattr(_model, "get_embedding_dimension") else _EMBEDDING_DIM
        logger.info(f"嵌入模型加载完成 ({time.time()-t:.1f}s, dim={dim})")
        return _model
    except Exception as e:
        logger.error(f"嵌入模型加载失败: {e}")
        return None


def is_available() -> bool:
    return _load_model() is not None


# ─── 向量运算 ───

def generate_embedding(text: str) -> np.ndarray | None:
    model = _load_model()
    if model is None:
        return None
    try:
        return model.encode(text, normalize_embeddings=True)
    except Exception as e:
        logger.error(f"编码失败: {e}")
        return None


def batch_generate_embeddings(texts: list[str], batch_size: int = 32) -> list[np.ndarray] | None:
    model = _load_model()
    if model is None:
        return None
    try:
        return model.encode(texts, batch_size=batch_size, normalize_embeddings=True, show_progress_bar=False)
    except Exception as e:
        logger.error(f"批量编码失败: {e}")
        return None


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))


# ─── 向量 → BLOB / BLOB → 向量 ───

def vector_to_blob(v: np.ndarray) -> bytes:
    return v.astype(np.float32).tobytes()


def blob_to_vector(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)


# ─── 存 / 取 ───

def encode_and_store(entity_type: str, entity_id: int, text: str) -> bool:
    vec = generate_embedding(text)
    if vec is None:
        return False
    blob = vector_to_blob(vec)
    with get_db() as db:
        db.execute(
            """INSERT OR REPLACE INTO embeddings (entity_type, entity_id, text, vector, updated_at)
               VALUES (?, ?, ?, ?, datetime('now','localtime'))""",
            (entity_type, entity_id, text, blob)
        )
        db.commit()
    return True


def encode_and_store_batch(entries: list[tuple[str, int, str]]) -> int:
    texts = [e[2] for e in entries]
    vecs = batch_generate_embeddings(texts)
    if vecs is None:
        return 0
    blobs = [vector_to_blob(v) for v in vecs]

    count = 0
    with get_db() as db:
        for (entity_type, entity_id, text), blob in zip(entries, blobs):
            db.execute(
                """INSERT OR REPLACE INTO embeddings (entity_type, entity_id, text, vector, updated_at)
                   VALUES (?, ?, ?, ?, datetime('now','localtime'))""",
                (entity_type, entity_id, text, blob)
            )
            count += 1
        db.commit()
    return count


def get_stored_embeddings(entity_type: str | None = None) -> list[dict]:
    with get_db() as db:
        if entity_type:
            rows = db.execute(
                "SELECT * FROM embeddings WHERE entity_type = ?", (entity_type,)
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM embeddings").fetchall()
        return rows_to_dicts(rows)


# ─── 语义搜索 ───

def semantic_search(
    query: str,
    entity_type: str | None = None,
    top_k: int = 5,
    min_score: float = 0.3,
) -> list[dict]:
    t = time.time()
    query_vec = generate_embedding(query)
    if query_vec is None:
        return []

    stored = get_stored_embeddings(entity_type)
    if not stored:
        return []

    results = []
    for s in stored:
        vec = blob_to_vector(s["vector"])
        score = cosine_similarity(query_vec, vec)
        if score >= min_score:
            results.append({
                "entity_type": s["entity_type"],
                "entity_id": s["entity_id"],
                "text": s["text"][:200],
                "score": round(float(score), 4),
            })

    results.sort(key=lambda x: x["score"], reverse=True)

    # 附加显示数据
    _attach_display_info(results[:top_k])

    logger.info(f"语义搜索 [{query}] → {len(results)} 匹配, 耗时 {time.time()-t:.3f}s")
    return results[:top_k]


def _attach_display_info(results: list[dict]):
    if not results:
        return

    diary_ids = [(r["entity_id"], r) for r in results if r["entity_type"] == "diary"]
    memory_ids = [(r["entity_id"], r) for r in results if r["entity_type"] == "memory"]
    milestone_ids = [(r["entity_id"], r) for r in results if r["entity_type"] == "milestone"]

    with get_db() as db:
        for ids, table, date_field, title_field, content_field in [
            (diary_ids, "diaries", "date", "title", "content"),
            (memory_ids, "memory_events", "date", "title", "content"),
            (milestone_ids, "milestones", "date", "title", "description"),
        ]:
            if not ids:
                continue
            id_list = [e[0] for e in ids]
            placeholders = ",".join("?" for _ in id_list)
            rows = db.execute(
                f"SELECT id, {date_field}, {title_field}, {content_field} FROM {table} WHERE id IN ({placeholders})",
                id_list
            ).fetchall()
            info_map = {r["id"]: r for r in rows_to_dicts(rows)} if hasattr(rows[0], "keys") else {}
            for eid, result in ids:
                info = info_map.get(eid, {})
                result["display_date"] = info.get(date_field, "")
                result["display_title"] = info.get(title_field, "")
                result["display_content"] = (info.get(content_field, "") or "")[:300]


# ─── 批量重建全部向量 ───

def rebuild_all(force: bool = False) -> dict:
    stats = {"diary": 0, "memory": 0, "milestone": 0, "total": 0}

    with get_db() as db:
        for entity_type, table, text_fields in [
            ("diary", "diaries", "title || ' ' || content"),
            ("memory", "memory_events", "title || ' ' || content"),
            ("milestone", "milestones", "title || ' ' || description"),
        ]:
            if not force:
                existing = db.execute(
                    "SELECT COUNT(*) FROM embeddings WHERE entity_type = ?", (entity_type,)
                ).fetchone()[0]
                db_count = db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                if existing >= db_count:
                    stats[entity_type] = existing
                    continue

            rows = db.execute(
                f"SELECT id, {text_fields} AS search_text FROM {table}"
            ).fetchall()

            entries = []
            for r in rows_to_dicts(rows):
                text = (r.get("search_text") or "").strip()
                if text:
                    entries.append((entity_type, r["id"], text))

            if entries:
                count = encode_and_store_batch(entries)
                stats[entity_type] = count
                stats["total"] += count

    stats["total"] = stats["diary"] + stats["memory"] + stats["milestone"]
    return stats


def get_stats() -> dict:
    with get_db() as db:
        total = db.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]
        by_type = {
            r["entity_type"]: r["cnt"]
            for r in rows_to_dicts(db.execute(
                "SELECT entity_type, COUNT(*) AS cnt FROM embeddings GROUP BY entity_type"
            ).fetchall())
        }
    return {"total": total, "by_type": by_type, "dimension": _EMBEDDING_DIM}
