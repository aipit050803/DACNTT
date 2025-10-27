# app/services/vector.py
from __future__ import annotations
from typing import List, Dict, Any
import os
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings

# Embedding model local (nhẹ, 384-d)
_EMB_MODEL_NAME = os.getenv("EMB_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
_sbert = SentenceTransformer(_EMB_MODEL_NAME)  # lần đầu tải ~100MB

# ChromaDB (persistent local)
CHROMA_DIR = os.getenv("CHROMA_DIR", ".chroma")
chroma_client = chromadb.PersistentClient(
    path=CHROMA_DIR,
    settings=Settings(anonymized_telemetry=False)
)
_COLLECTION = "study_docs"
_collection = chroma_client.get_or_create_collection(name=_COLLECTION)

def embed_texts(texts: list[str]) -> list[list[float]]:
    vecs = _sbert.encode(
        texts,
        convert_to_numpy=True,      # để .tolist() OK
        normalize_embeddings=True
    )
    return vecs.tolist()

def upsert_doc(doc_id: str, chunks: List[str]) -> None:
    if not chunks:
        return
    embeddings = embed_texts(chunks)
    ids = [f"{doc_id}-{i}" for i in range(len(chunks))]
    metas = [{"doc_id": doc_id, "idx": i} for i in range(len(chunks))]
    _collection.upsert(ids=ids, documents=chunks, metadatas=metas, embeddings=embeddings)

def search_similar(query: str, k: int = 6) -> List[Dict[str, Any]]:
    emb = embed_texts([query])[0]
    res = _collection.query(query_embeddings=[emb], n_results=k)
    out: List[Dict[str, Any]] = []
    for docs, metas in zip(res.get("documents", [[]])[0], res.get("metadatas", [[]])[0]):
        out.append({"text": docs, "meta": metas or {}})
    return out
