import os
import json
import numpy as np
import faiss
from typing import List, Optional, Tuple
from sentence_transformers import SentenceTransformer
from app.config import settings

_model: Optional[SentenceTransformer] = None
_index: Optional[faiss.IndexFlatIP] = None
_log_ids: List[str] = []
_dimension: int = 384


def get_embedding_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(settings.embedding_model)
    return _model


def encode_texts(texts: List[str]) -> np.ndarray:
    model = get_embedding_model()
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return np.array(embeddings, dtype=np.float32)


def build_index(log_docs: List[dict]) -> Tuple[faiss.IndexFlatIP, List[str]]:
    global _index, _log_ids, _dimension

    if not log_docs:
        _index = faiss.IndexFlatIP(_dimension)
        _log_ids = []
        return _index, _log_ids

    texts = []
    ids = []
    for doc in log_docs:
        text = doc.get("embedding_text") or ""
        if not text:
            text = f"module:{doc.get('module','')} action:{doc.get('action','')} category:{doc.get('category','')}"
        texts.append(text)
        ids.append(doc["log_id"])

    embeddings = encode_texts(texts)
    _dimension = embeddings.shape[1]
    _index = faiss.IndexFlatIP(_dimension)
    _index.add(embeddings)
    _log_ids = ids

    save_index()
    return _index, _log_ids


def search(query: str, top_k: int = 10, allowed_log_ids: Optional[List[str]] = None) -> List[Tuple[str, float]]:
    global _index, _log_ids

    if _index is None or _index.ntotal == 0:
        return []

    query_vec = encode_texts([query])
    k = min(top_k * 3 if allowed_log_ids else top_k, _index.ntotal)
    scores, indices = _index.search(query_vec, k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0 or idx >= len(_log_ids):
            continue
        log_id = _log_ids[idx]
        if allowed_log_ids is not None and log_id not in allowed_log_ids:
            continue
        results.append((log_id, float(score)))
        if len(results) >= top_k:
            break

    return results


def add_to_index(log_doc: dict) -> None:
    global _index, _log_ids, _dimension
    if _index is None:
        _index = faiss.IndexFlatIP(_dimension)
        _log_ids = []

    text = log_doc.get("embedding_text") or ""
    if not text:
        text = f"module:{log_doc.get('module','')} action:{log_doc.get('action','')} category:{log_doc.get('category','')}"

    embedding = encode_texts([text])
    _index.add(embedding)
    _log_ids.append(log_doc["log_id"])
    save_index()


def save_index():
    global _index, _log_ids
    os.makedirs(os.path.dirname(settings.faiss_index_path) or ".", exist_ok=True)
    if _index is not None:
        faiss.write_index(_index, settings.faiss_index_path + ".bin")
    with open(settings.faiss_index_path + ".ids.json", "w") as f:
        json.dump(_log_ids, f)


def load_index() -> bool:
    global _index, _log_ids, _dimension
    bin_path = settings.faiss_index_path + ".bin"
    ids_path = settings.faiss_index_path + ".ids.json"
    if os.path.exists(bin_path) and os.path.exists(ids_path):
        _index = faiss.read_index(bin_path)
        with open(ids_path, "r") as f:
            _log_ids = json.load(f)
        _dimension = _index.d
        return True
    return False
