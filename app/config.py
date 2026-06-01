import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GOOGLE_CSE_API_KEY = os.getenv("GOOGLE_CSE_API_KEY", "")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID", "")
JINA_API_KEY = os.getenv("JINA_API_KEY", "")
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")

GEN_MODEL = "gemini-2.5-flash"
EMBED_MODEL = "gemini-embedding-001"
EMBED_DIM = 768
CHUNK_SIZE = 512
CHUNK_OVERLAP = 64
TOP_K = 20  # always fetch max; UI filters client-side
MAX_URLS = 10
