import math
import time
import logging
import numpy as np
from app.services.gemini_client import safe_embed

logger = logging.getLogger(__name__)

_BATCH_SIZE = 100
_INTER_BATCH_DELAY = 25.0  # free tier: 100 requests/min, wait between batches


def embed_texts(texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT") -> np.ndarray:
    if not texts:
        raise ValueError("No texts to embed")

    all_embeddings = []
    n_batches = math.ceil(len(texts) / _BATCH_SIZE)
    logger.info(f"Embedding {len(texts)} texts in {n_batches} batch(es)")

    for i in range(n_batches):
        if i > 0:
            logger.info(f"Rate limit pause {_INTER_BATCH_DELAY}s between batches...")
            time.sleep(_INTER_BATCH_DELAY)
        batch = texts[i * _BATCH_SIZE : (i + 1) * _BATCH_SIZE]
        embeddings = safe_embed(batch, task_type=task_type)
        all_embeddings.extend([e.values for e in embeddings])

    arr = np.array(all_embeddings, dtype="float32")
    logger.info(f"Embedding complete: shape={arr.shape}")
    return arr
