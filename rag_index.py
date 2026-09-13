"""Task 3: real local embeddings, two persistent Chroma indexes, and retrieval.

This returns source passages, not generated answers or calibrated confidence.
Run prepare_model.py once with internet access before using these offline commands.
"""

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re

from rag_config import (
    CHUNK_OVERLAP, CHUNK_SIZE, COLLECTION_NAMES, DB_DIR, KB_DIR,
    MODEL_DIR, MODEL_ID, MODEL_REVISION, SENTENCES_PER_CHUNK,
)


@dataclass(frozen=True)
class Document:
    doc_id: str
    title: str
    body: str
    source_sha256: str


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    body: str
    strategy: str
    position: int
    start_char: int
    end_char: int
    source_sha256: str

    @property
    def text(self):
        # The same title prefix is used for both strategies; offsets refer to body.
        return f"{self.title}\n{self.body}"

    @property
    def metadata(self):
        return {
            "doc_id": self.doc_id, "title": self.title,
            "source": f"knowledge_base/{self.doc_id}",
            "strategy": self.strategy, "position": self.position,
            "start_char": self.start_char, "end_char": self.end_char,
            "source_sha256": self.source_sha256,
        }


def load_documents(kb_dir=KB_DIR):
    documents = []
    for path in sorted(Path(kb_dir).glob("*.md")):
        raw = path.read_bytes()
        lines = raw.decode("utf-8").strip().splitlines()
        if not lines or not lines[0].startswith("# "):
            raise ValueError(f"Policy needs a first-line heading: {path.name}")
        body = re.sub(r"\s+", " ", " ".join(lines[1:])).strip()
        if not body:
            raise ValueError(f"Policy has no body: {path.name}")
        documents.append(Document(path.name, lines[0][2:].strip(), body,
                                  hashlib.sha256(raw).hexdigest()))
    if not documents:
        raise ValueError(f"No policy documents found in {kb_dir}")
    return documents


def fixed_spans(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError("Require size > 0 and 0 <= overlap < size")
    spans = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        spans.append((start, end))
        if end == len(text):
            break
        start = end - overlap
    return spans


def sentence_spans(text, group_size=SENTENCES_PER_CHUNK):
    """Group complete sentences in these authored policies; no external tokenizer.

    Their punctuation avoids ambiguous abbreviations/decimals. If future documents
    introduce those forms, upgrade this boundary splitter before indexing them.
    """
    if group_size < 1:
        raise ValueError("Sentence group size must be positive")
    parts = [(match.start(), match.end()) for match in
             re.finditer(r"\S.*?(?:[.!?](?=\s|$)|$)", text)]
    return [(parts[i][0], parts[min(i + group_size, len(parts)) - 1][1])
            for i in range(0, len(parts), group_size)]


def make_chunks(documents, strategy):
    if strategy not in COLLECTION_NAMES:
        raise ValueError(f"Unknown strategy: {strategy}")
    chunks = []
    for doc in documents:
        spans = fixed_spans(doc.body) if strategy == "fixed" else sentence_spans(doc.body)
        for position, (start, end) in enumerate(spans):
            chunks.append(Chunk(
                f"{strategy}:{doc.doc_id}:{position:04d}", doc.doc_id, doc.title,
                doc.body[start:end], strategy, position, start, end, doc.source_sha256,
            ))
    return chunks


def fingerprint(documents):
    content = "\n".join(f"{doc.doc_id}:{doc.source_sha256}" for doc in documents)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def offline_environment():
    # Set before importing either dependency; no provider-generated embeddings.
    for key, value in {
        "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1", "ANONYMIZED_TELEMETRY": "False",
        "OTEL_SDK_DISABLED": "true", "TOKENIZERS_PARALLELISM": "false",
    }.items():
        os.environ[key] = value


class PolicyIndex:
    def __init__(self, kb_dir=KB_DIR, db_dir=DB_DIR, model_dir=MODEL_DIR):
        offline_environment()
        self.kb_dir = Path(kb_dir)
        self.db_dir = Path(db_dir)
        model_dir = Path(model_dir)
        marker = model_dir / "capstone_model.json"
        if not marker.is_file():
            raise FileNotFoundError("Local model is missing; run python prepare_model.py first")
        expected = {"model_id": MODEL_ID, "revision": MODEL_REVISION}
        if json.loads(marker.read_text(encoding="utf-8")) != expected:
            raise ValueError("Local model does not match the pinned project model")
        import chromadb
        from chromadb.config import Settings
        from sentence_transformers import SentenceTransformer
        import torch

        torch.set_num_threads(2)
        self.model = SentenceTransformer(str(model_dir), device="cpu",
                                         local_files_only=True, trust_remote_code=False)
        self.client = chromadb.PersistentClient(
            path=str(self.db_dir), settings=Settings(anonymized_telemetry=False)
        )

    def _metadata(self, strategy, documents):
        return {
            "project": "ola_capstone", "strategy": strategy,
            "model_id": MODEL_ID, "model_revision": MODEL_REVISION,
            "dimension": int(self.model.get_sentence_embedding_dimension()),
            "normalized_embeddings": True, "kb_fingerprint": fingerprint(documents),
            "chunk_config": json.dumps({
                "size": CHUNK_SIZE, "overlap": CHUNK_OVERLAP,
                "sentence_group_size": SENTENCES_PER_CHUNK,
                "title_prefix": True, "format_version": 1,
            }, sort_keys=True),
        }

    def _check_metadata(self, collection, expected, check_fingerprint=True):
        actual = collection.metadata or {}
        keys = [key for key in expected if check_fingerprint or key != "kb_fingerprint"]
        if any(actual.get(key) != expected[key] for key in keys):
            raise ValueError(
                f"Index {collection.name} has stale or incompatible metadata; "
                "rebuild with the matching settings in a fresh project database"
            )
        if collection.configuration.get("hnsw", {}).get("space") != "cosine":
            raise ValueError(f"Index {collection.name} does not use cosine distance")

    def build(self):
        documents = load_documents(self.kb_dir)
        if len(documents) < 12:
            raise ValueError("The capstone requires at least 12 policy documents")
        summary = {"documents": len(documents), "model": MODEL_ID,
                   "model_revision": MODEL_REVISION, "collections": {}}
        for strategy, name in COLLECTION_NAMES.items():
            chunks = make_chunks(documents, strategy)
            metadata = self._metadata(strategy, documents)
            collection = self.client.get_or_create_collection(
                name=name, embedding_function=None, metadata=metadata,
                configuration={"hnsw": {"space": "cosine"}},
            )
            self._check_metadata(collection, metadata, check_fingerprint=False)
            # Reject silent model truncation rather than losing policy content.
            token_lengths = [len(self.model.tokenizer(chunk.text)["input_ids"])
                             for chunk in chunks]
            if max(token_lengths) > self.model.max_seq_length:
                raise ValueError("A chunk exceeds the model token limit; reduce chunk size")
            vectors = self.model.encode([chunk.text for chunk in chunks], batch_size=32,
                                        normalize_embeddings=True, show_progress_bar=False)
            old_ids = set(collection.get(include=["metadatas"])["ids"])
            new_ids = {chunk.chunk_id for chunk in chunks}
            # Both indexes explicitly use upsert as required by the assignment.
            collection.upsert(
                ids=[chunk.chunk_id for chunk in chunks], embeddings=vectors.tolist(),
                documents=[chunk.text for chunk in chunks],
                metadatas=[chunk.metadata for chunk in chunks],
            )
            stale_ids = sorted(old_ids - new_ids)
            if stale_ids:
                collection.delete(ids=stale_ids)
            collection.modify(metadata=metadata)
            if collection.count() != len(chunks):
                raise RuntimeError(f"Incorrect stored chunk count in {name}")
            summary["collections"][strategy] = {
                "name": name, "chunks": collection.count(),
                "dimensions": vectors.shape[1], "distance": "cosine",
                "max_chunk_tokens": max(token_lengths),
                "stale_chunks_removed": len(stale_ids),
            }
        return summary

    def query(self, question, strategy="fixed", top_k=3):
        if strategy not in COLLECTION_NAMES:
            raise ValueError(f"Unknown strategy: {strategy}")
        question = question.strip()
        if not question or top_k < 1:
            raise ValueError("Provide a nonempty question and top_k >= 1")
        documents = load_documents(self.kb_dir)
        collection = self.client.get_collection(
            name=COLLECTION_NAMES[strategy], embedding_function=None
        )
        self._check_metadata(collection, self._metadata(strategy, documents))
        if not collection.count():
            raise ValueError("The collection is empty; run python rag_index.py build")
        if len(self.model.tokenizer(question)["input_ids"]) > self.model.max_seq_length:
            raise ValueError("Question exceeds the embedding model token limit")
        vector = self.model.encode([question], normalize_embeddings=True,
                                   show_progress_bar=False)
        result = collection.query(query_embeddings=vector.tolist(),
                                  n_results=min(top_k, collection.count()),
                                  include=["documents", "metadatas", "distances"])
        hits = []
        for chunk_id, text, meta, distance in zip(
            result["ids"][0], result["documents"][0],
            result["metadatas"][0], result["distances"][0],
        ):
            hits.append({"chunk_id": chunk_id, "doc_id": meta["doc_id"],
                         "source": meta["source"], "title": meta["title"],
                         "cosine_similarity": round(1.0 - float(distance), 6),
                         "text": text})
        return {"question": question, "strategy": strategy, "hits": hits}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("build", help="Embed and upsert both persistent collections")
    query = commands.add_parser("query", help="Retrieve source passages from an index")
    query.add_argument("question")
    query.add_argument("--strategy", choices=tuple(COLLECTION_NAMES), default="fixed")
    query.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()
    index = PolicyIndex()
    result = index.build() if args.command == "build" else index.query(
        args.question, args.strategy, args.top_k
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
