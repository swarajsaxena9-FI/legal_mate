import logging
import numpy as np
import faiss
from app.config import TOP_K

logger = logging.getLogger(__name__)


def top_k_matches(
    query_vec: np.ndarray,
    chunk_vecs: np.ndarray,
    chunks: list[dict],
    k: int = TOP_K,
) -> list[dict]:
    chunk_vecs = chunk_vecs.copy().astype("float32")
    query_vec = query_vec.copy().astype("float32")

    if query_vec.ndim == 1:
        query_vec = query_vec.reshape(1, -1)

    faiss.normalize_L2(chunk_vecs)
    index = faiss.IndexFlatIP(chunk_vecs.shape[1])
    index.add(chunk_vecs)

    faiss.normalize_L2(query_vec)
    k = min(k, len(chunks))
    scores, idxs = index.search(query_vec, k)

    results = []
    for score, idx in zip(scores[0], idxs[0]):
        if idx < 0:
            continue
        results.append({
            "score": float(score),
            "url": chunks[idx]["url"],
            "text": chunks[idx]["text"],
            "chunk_index": chunks[idx].get("chunk_index", idx),
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    logger.info(f"FAISS search: top-{k} results, best score={results[0]['score']:.4f}" if results else "No results")
    return results
