"""Shared settings for the local embedding model and the two Task 3 indexes."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
KB_DIR = PROJECT_ROOT / "knowledge_base"
MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
MODEL_DIR = PROJECT_ROOT / "models" / "all-MiniLM-L6-v2"
DB_DIR = PROJECT_ROOT / "storage" / "chroma"
CHUNK_SIZE = 400
CHUNK_OVERLAP = 80
SENTENCES_PER_CHUNK = 2
COLLECTION_NAMES = {
    "fixed": "ola_fixed_v1",
    "sentence": "ola_sentence_v1",
}

# Chosen from the measured Portion 2 calibration set. See
# transcripts/portion2_evidence.json and TASK4-5-GROUNDED-ANSWERS.md.
DEFAULT_RETRIEVAL_STRATEGY = "sentence"
FALLBACK_THRESHOLD = 0.40
FALLBACK_MESSAGE = (
    "I do not have enough support-policy information to answer that question."
)
