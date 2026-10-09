from pathlib import Path
from typing import Dict, Any, Optional
import chromadb
from chromadb.utils import embedding_functions

STORAGE_DIR = Path(__file__).resolve().parent
CHROMA_DIR = STORAGE_DIR / "chroma_db"


class ResumeVectorStore:
    """Manages embedding generation with all-MiniLM-L6-v2 (ONNX) and storage in local ChromaDB."""

    def __init__(self, persist_dir: Path = CHROMA_DIR):
        self.persist_dir = persist_dir
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(self.persist_dir))
        self.embedding_fn = embedding_functions.ONNXMiniLM_L6_V2()
        self.collection = self.client.get_or_create_collection(
            name="resumes",
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )

    def add_resume(
        self,
        user_name: str,
        resume_text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Convert resume text to vector embedding and store in ChromaDB collection."""
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
        """Perform vector similarity search against ChromaDB collection."""
        return self.collection.query(
            query_texts=[query_text], n_results=n_results
        )


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
    """Convenience function to store resume text vector in local ChromaDB."""
    store = get_vector_store()
    return store.add_resume(user_name, resume_text, metadata)


def get_resume_embedding_by_user(user_name: str = "Candidate") -> Dict[str, Any]:
    """Retrieve stored document and vector embedding metadata from Chroma vector store for user_name."""
    name = user_name or "Candidate"
    doc_id = f"resume_{name.lower().replace(' ', '_')}"
    store = get_vector_store()
    res = store.collection.get(
        ids=[doc_id], include=["embeddings", "documents", "metadatas"]
    )
    if res and res.get("ids") and len(res["ids"]) > 0:
        embeddings = res.get("embeddings")
        dims = len(embeddings[0]) if embeddings is not None and len(embeddings) > 0 else 0
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


def search_resume_vector_store(query_text: str = "ping", n_results: int = 5) -> Dict[str, Any]:
    """Query Chroma vector store with query_text and return JSON-serializable Python types."""
    q_text = query_text if query_text and query_text.strip() else "ping"
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
