import logging
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.config import CHUNK_SIZE, CHUNK_OVERLAP

logger = logging.getLogger(__name__)

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=["\n\n", "\n", ". ", " ", ""],
)


def chunk_documents(docs: list[dict]) -> list[dict]:
    chunks = []
    for doc in docs:
        url = doc["url"]
        text = doc["text"]
        splits = _splitter.split_text(text)
        for i, split in enumerate(splits):
            if split.strip():
                chunks.append({"url": url, "text": split.strip(), "chunk_index": i})
    # Cap at 20 chunks: free tier = 100 embed req/min, 20 chunks uses only 20% allowing ~4 searches/min
    if len(chunks) > 20:
        logger.info(f"Capping chunks from {len(chunks)} to 20 for free-tier quota")
        chunks = chunks[:20]
    logger.info(f"Chunked {len(docs)} docs into {len(chunks)} chunks")
    return chunks
