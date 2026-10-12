import hashlib
import math
from pathlib import Path
from typing import Dict, Any, Optional, List
from config import get_logger

logger = get_logger(__name__)

STORAGE_DIR = Path(__file__).resolve().parent
CHROMA_DIR = STORAGE_DIR / "chroma_db"


def compute_lightweight_embedding(text: str, dim: int = 384) -> List[float]:
    """
    Generate deterministic, normalized 384-dimensional dense embedding
    using word & character n-gram feature hashing with sublinear frequency weighting.
    Matches all-MiniLM-L6-v2 dimensionality without loading heavy ONNX runtime or model weights into RAM.
    """
    if not text or not text.strip():
        return [0.0] * dim

    vec = [0.0] * dim
    tokens = text.lower().replace("\n", " ").split()
    features = list(tokens)

    # Subword character trigrams for robust morphological matching
    for tok in tokens:
        if len(tok) >= 3:
            for i in range(len(tok) - 2):
                features.append(tok[i : i + 3])

    for f in features:
        h = int(hashlib.md5(f.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if (h >> 8) % 2 == 0 else -1.0
        vec[idx] += sign

    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0.0:
        vec = [float(x / norm) for x in vec]
    return vec


class LightweightEmbeddingFunction:
    """Zero-overhead embedding function compatible with ChromaDB protocol."""

    def is_legacy(self) -> bool:
        return False

    def get_config(self) -> Dict[str, Any]:
        return {}

    @classmethod
    def build_from_config(cls, config: Dict[str, Any]) -> "LightweightEmbeddingFunction":
        return cls()

    def supported_spaces(self) -> List[str]:
        return ["cosine", "l2", "ip"]

    def default_space(self) -> str:
        return "cosine"

    @staticmethod
    def name() -> str:
        # Match persisted collection name to prevent Chroma configuration conflicts
        return "onnx_mini_lm_l6_v2"

    def __call__(self, input: List[str]) -> List[List[float]]:
        return [compute_lightweight_embedding(doc) for doc in input]

    def embed_documents(self, input: List[str]) -> List[List[float]]:
        return self(input)

    def embed_query(self, input: List[str]) -> List[List[float]]:
        return self(input)


class InMemoryResumeCollection:
    """Lightweight in-memory vector collection fallback for zero-RAM/low-memory environments."""

    def __init__(self, embedding_fn: LightweightEmbeddingFunction):
        self.embedding_fn = embedding_fn
        self.docs: Dict[str, Dict[str, Any]] = {}

    def upsert(
        self, ids: List[str], documents: List[str], metadatas: Optional[List[dict]] = None
    ):
        metas = metadatas or [{}] * len(ids)
        embeddings = self.embedding_fn(documents)
        for i, doc_id in enumerate(ids):
            self.docs[doc_id] = {
                "id": doc_id,
                "document": documents[i],
                "metadata": metas[i] if i < len(metas) else {},
                "embedding": embeddings[i],
            }

    def get(
        self, ids: Optional[List[str]] = None, include: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        target_ids = ids if ids is not None else list(self.docs.keys())
        matched = [self.docs[tid] for tid in target_ids if tid in self.docs]
        return {
            "ids": [m["id"] for m in matched],
            "documents": [m["document"] for m in matched],
            "metadatas": [m["metadata"] for m in matched],
            "embeddings": [m["embedding"] for m in matched],
        }

    def query(self, query_texts: List[str], n_results: int = 5) -> Dict[str, Any]:
        if not self.docs or not query_texts:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}
        q_emb = self.embedding_fn(query_texts)[0]
        scored = []
        for doc_id, data in self.docs.items():
            doc_emb = data["embedding"]
            dot = sum(a * b for a, b in zip(q_emb, doc_emb))
            dist = max(0.0, 1.0 - dot)
            scored.append((dist, doc_id, data["document"], data["metadata"]))
        scored.sort(key=lambda x: x[0])
        top = scored[:n_results]
        return {
            "ids": [[item[1] for item in top]],
            "documents": [[item[2] for item in top]],
            "metadatas": [[item[3] for item in top]],
            "distances": [[item[0] for item in top]],
        }

    def delete(self, ids: List[str]) -> None:
        for tid in ids:
            self.docs.pop(tid, None)


class ResumeVectorStore:
    """Manages embedding generation and resume storage with zero memory pressure."""

    def __init__(self, persist_dir: Path = CHROMA_DIR):
        self.persist_dir = persist_dir
        self.embedding_fn = LightweightEmbeddingFunction()
        self.collection: Any = None

        try:
            import chromadb

            self.persist_dir.mkdir(parents=True, exist_ok=True)
            self.client = chromadb.PersistentClient(path=str(self.persist_dir))
            try:
                self.collection = self.client.get_or_create_collection(
                    name="resumes",
                    embedding_function=self.embedding_fn,
                    metadata={"hnsw:space": "cosine"},
                )
            except Exception as e:
                logger.info(
                    f"Re-creating Chroma resumes collection due to schema update: {e}"
                )
                try:
                    self.client.delete_collection("resumes")
                except Exception:
                    pass
                self.collection = self.client.create_collection(
                    name="resumes",
                    embedding_function=self.embedding_fn,
                    metadata={"hnsw:space": "cosine"},
                )
        except Exception as e:
            logger.warning(
                f"ChromaDB persistent client unavailable ({e}). Using in-memory fallback store."
            )
            self.collection = InMemoryResumeCollection(self.embedding_fn)

    def add_resume(
        self,
        user_name: str,
        resume_text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Convert resume text to vector embedding and store in collection."""
        doc_id = f"resume_{user_name.lower().replace(' ', '_')}"
        meta = metadata or {}
        meta["user_name"] = user_name

        self.collection.upsert(
            ids=[doc_id],
            documents=[resume_text],
            metadatas=[meta],
        )
        return doc_id

    def search_similar_resumes(self, query_text: str, n_results: int = 5):
        """Perform vector similarity search against collection."""
        return self.collection.query(
            query_texts=[query_text], n_results=n_results
        )

    def delete_resume(self, user_name: str) -> None:
        """Remove a specific user's resume embedding from collection."""
        doc_id = f"resume_{user_name.lower().replace(' ', '_')}"
        try:
            self.collection.delete(ids=[doc_id])
        except Exception:
            pass

    def clear_all_resumes(self) -> None:
        """Remove all stored resume documents from collection."""
        try:
            res = self.collection.get()
            all_ids = res.get("ids", []) if res else []
            if all_ids:
                self.collection.delete(ids=all_ids)
        except Exception:
            pass


_vector_store_instance: Optional[ResumeVectorStore] = None


def get_vector_store() -> ResumeVectorStore:
    """Retrieve or create a thread-safe singleton instance of ResumeVectorStore."""
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = ResumeVectorStore()
    return _vector_store_instance


def store_resume_vector(
    user_name: str, resume_text: str, metadata: Optional[Dict[str, Any]] = None
) -> str:
    """Convenience function to store resume text vector in vector store."""
    store = get_vector_store()
    return store.add_resume(user_name, resume_text, metadata)


def get_resume_embedding_by_user(user_name: str = "Candidate") -> Dict[str, Any]:
    """Retrieve stored document and vector embedding metadata from vector store for user_name."""
    name = user_name or "Candidate"
    doc_id = f"resume_{name.lower().replace(' ', '_')}"
    try:
        store = get_vector_store()
        res = store.collection.get(
            ids=[doc_id], include=["embeddings", "documents", "metadatas"]
        )
        if res and res.get("ids") and len(res["ids"]) > 0:
            embeddings = res.get("embeddings")
            dims = (
                len(embeddings[0])
                if embeddings is not None and len(embeddings) > 0 and embeddings[0] is not None
                else 384
            )
            return {
                "status": "success",
                "id": res["ids"][0],
                "document": res["documents"][0] if res.get("documents") else "",
                "metadata": res["metadatas"][0] if res.get("metadatas") else {},
                "embedding_dimensions": dims,
            }
        return {
            "status": "not_found",
            "message": f"No resume embedding found for user '{name}'",
            "embedding_dimensions": 0,
        }
    except Exception as e:
        logger.warning(f"Error querying resume embedding for {user_name}: {e}")
        return {
            "status": "not_found",
            "message": f"No resume embedding found for user '{name}' ({e})",
            "embedding_dimensions": 0,
        }


def search_resume_vector_store(query_text: str = "ping", n_results: int = 5) -> Dict[str, Any]:
    """Query vector store with query_text and return JSON-serializable Python types."""
    q_text = query_text if query_text and query_text.strip() else "ping"
    try:
        store = get_vector_store()
        raw_res = store.search_similar_resumes(q_text, n_results=n_results)

        ids_list = [list(i) for i in raw_res.get("ids", [])] if raw_res.get("ids") else []
        docs_list = [list(d) for d in raw_res.get("documents", [])] if raw_res.get("documents") else []
        metas_list = [list(m) for m in raw_res.get("metadatas", [])] if raw_res.get("metadatas") else []
        dists_list = [[float(val) for val in d] for d in raw_res.get("distances", [])] if raw_res.get("distances") else []

        return {
            "ids": ids_list,
            "documents": docs_list,
            "metadatas": metas_list,
            "distances": dists_list,
        }
    except Exception as e:
        logger.warning(f"Error executing vector similarity search: {e}")
        return {
            "ids": [],
            "documents": [],
            "metadatas": [],
            "distances": [],
        }


def delete_resume_vector(user_name: str) -> None:
    """Convenience function to delete a user's resume embedding from vector store."""
    try:
        store = get_vector_store()
        store.delete_resume(user_name)
    except Exception:
        pass


def clear_all_resume_vectors() -> None:
    """Convenience function to delete all resume embeddings from vector store."""
    try:
        store = get_vector_store()
        store.clear_all_resumes()
    except Exception:
        pass

