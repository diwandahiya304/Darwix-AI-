"""Vector store abstraction — swappable via VECTOR_STORE_BACKEND
(chroma | qdrant), both running fully local (no server process needed).

Chroma is the default: simplest local persistent-client API for this
corpus's scale. Qdrant is implemented and verified as the alternative
(its Python client also supports a fully local, file-backed mode via
`QdrantClient(path=...)`, no server required either) — see
docs/DECISIONS.md for why both were kept rather than picking one.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class VectorHit:
    def __init__(self, id: str, score: float, metadata: dict, document: str):
        self.id = id
        self.score = score  # cosine similarity, 0..1 (higher = more similar)
        self.metadata = metadata
        self.document = document


class VectorStore(Protocol):
    def upsert(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
        documents: list[str],
    ) -> None: ...

    def query(
        self, embedding: list[float], top_k: int, where: dict | None = None
    ) -> list[VectorHit]: ...

    def count(self) -> int: ...

    def reset(self) -> None: ...


class ChromaVectorStore:
    _COLLECTION_NAME = "kb_records"

    def __init__(self, path: Path):
        import chromadb

        path.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(path))
        self._collection = self._client.get_or_create_collection(
            self._COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
        )

    def upsert(self, ids, embeddings, metadatas, documents) -> None:
        if not ids:
            return
        self._collection.upsert(
            ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents
        )

    def query(self, embedding, top_k, where=None) -> list[VectorHit]:
        if self.count() == 0:
            return []
        chroma_where = None
        if where:
            # Chroma needs $and for multiple equality conditions; a single
            # condition can be a bare {key: value}.
            if len(where) == 1:
                key, value = next(iter(where.items()))
                chroma_where = {key: value}
            else:
                chroma_where = {"$and": [{k: v} for k, v in where.items()]}
        result = self._collection.query(
            query_embeddings=[embedding],
            n_results=min(top_k, self.count()),
            where=chroma_where,
        )
        hits: list[VectorHit] = []
        ids = result["ids"][0]
        distances = result["distances"][0]
        metadatas = result["metadatas"][0]
        documents = result["documents"][0]
        for id_, distance, metadata, document in zip(ids, distances, metadatas, documents):
            # Chroma's hnsw cosine "distance" is 1 - cosine_similarity.
            similarity = 1.0 - distance
            hits.append(VectorHit(id=id_, score=similarity, metadata=metadata, document=document))
        return hits

    def count(self) -> int:
        return self._collection.count()

    def reset(self) -> None:
        self._client.delete_collection(self._COLLECTION_NAME)
        self._collection = self._client.get_or_create_collection(
            self._COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
        )


class QdrantVectorStore:
    _COLLECTION_NAME = "kb_records"

    def __init__(self, path: Path, vector_size: int = 384):
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams

        path.mkdir(parents=True, exist_ok=True)
        self._client = QdrantClient(path=str(path))
        self._vector_size = vector_size
        if not self._client.collection_exists(self._COLLECTION_NAME):
            self._client.create_collection(
                self._COLLECTION_NAME,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
        self._id_map: dict[int, str] = {}  # qdrant needs int/uuid point ids

    def _point_id(self, record_id: str) -> int:
        import hashlib

        return int(hashlib.sha256(record_id.encode("utf-8")).hexdigest()[:15], 16)

    def upsert(self, ids, embeddings, metadatas, documents) -> None:
        if not ids:
            return
        from qdrant_client.models import PointStruct

        points = []
        for id_, embedding, metadata, document in zip(ids, embeddings, metadatas, documents):
            point_id = self._point_id(id_)
            self._id_map[point_id] = id_
            payload = {**metadata, "_record_id": id_, "_document": document}
            points.append(PointStruct(id=point_id, vector=embedding, payload=payload))
        self._client.upsert(self._COLLECTION_NAME, points=points)

    def query(self, embedding, top_k, where=None) -> list[VectorHit]:
        if self.count() == 0:
            return []
        query_filter = None
        if where:
            from qdrant_client.models import FieldCondition, Filter, MatchValue

            query_filter = Filter(
                must=[FieldCondition(key=k, match=MatchValue(value=v)) for k, v in where.items()]
            )
        result = self._client.query_points(
            self._COLLECTION_NAME,
            query=embedding,
            limit=top_k,
            query_filter=query_filter,
        )
        hits: list[VectorHit] = []
        for point in result.points:
            payload = dict(point.payload or {})
            record_id = payload.pop("_record_id", str(point.id))
            document = payload.pop("_document", "")
            hits.append(VectorHit(id=record_id, score=point.score, metadata=payload, document=document))
        return hits

    def count(self) -> int:
        return self._client.count(self._COLLECTION_NAME).count

    def reset(self) -> None:
        # NOT delete_collection()+create_collection(): reproducibly leaves
        # stale points behind in qdrant-client's local (embedded, no-server)
        # storage mode — verified directly, even a brand-new QdrantClient
        # pointed at the same on-disk path still sees the "deleted"
        # collection's old point count. Point-level delete-by-filter does
        # not have this problem. See docs/DECISIONS.md.
        from qdrant_client.models import Filter, FilterSelector

        if self._client.collection_exists(self._COLLECTION_NAME):
            self._client.delete(
                self._COLLECTION_NAME, points_selector=FilterSelector(filter=Filter())
            )
            return

        from qdrant_client.models import Distance, VectorParams

        self._client.create_collection(
            self._COLLECTION_NAME,
            vectors_config=VectorParams(size=self._vector_size, distance=Distance.COSINE),
        )


def get_vector_store(backend: str, path: Path, vector_size: int = 384) -> VectorStore:
    """vector_size defaults to 384 — intfloat/multilingual-e5-small's
    actual output dimension. Chroma infers dimension from the first
    upsert regardless; Qdrant validates it strictly at collection-create
    time, so tests using fake low-dimensional vectors must override it."""

    if backend == "chroma":
        return ChromaVectorStore(path)
    if backend == "qdrant":
        return QdrantVectorStore(path, vector_size=vector_size)
    raise ValueError(f"Unknown VECTOR_STORE_BACKEND: {backend!r} (expected 'chroma' or 'qdrant')")
