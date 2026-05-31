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
    # Cap at 100 chunks to stay within free-tier embedding quota (100 req/min)
    if len(chunks) > 100:
        logger.info(f"Capping chunks from {len(chunks)} to 100 for free-tier quota")
        chunks = chunks[:100]
    logger.info(f"Chunked {len(docs)} docs into {len(chunks)} chunks")
    return chunks
