"""
Qdrant vector store for VidyutSeva.
Manages 4 collections: outage_history, call_memory, bescom_knowledge, crowd_reports.
Uses OpenAI text-embedding-3-small (1536-dim).
"""

import os
import uuid
from dotenv import load_dotenv
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
    Filter,
    FieldCondition,
    MatchValue,
)

load_dotenv()

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536

COLLECTIONS = [
    "outage_history",
    "call_memory",
    "bescom_knowledge",
    "crowd_reports",
]

_qdrant: QdrantClient | None = None
_openai: OpenAI | None = None


def _get_qdrant() -> QdrantClient:
    global _qdrant
    if _qdrant is None:
        url = os.getenv("QDRANT_URL")
        api_key = os.getenv("QDRANT_API_KEY")
        if not url:
            raise RuntimeError("QDRANT_URL must be set in .env")
        _qdrant = QdrantClient(url=url, api_key=api_key)
    return _qdrant


def _get_openai() -> OpenAI:
    global _openai
    if _openai is None:
        _openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _openai


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

def init_collections() -> None:
    """Create collections if they don't exist."""
    client = _get_qdrant()
    existing = {c.name for c in client.get_collections().collections}
    for name in COLLECTIONS:
        if name not in existing:
            client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(
                    size=EMBEDDING_DIM, distance=Distance.COSINE
                ),
            )
            print(f"[Qdrant] Created collection: {name}")
        else:
            print(f"[Qdrant] Collection exists: {name}")


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------

def embed_text(text: str) -> list[float]:
    """Generate embedding vector for text via OpenAI."""
    client = _get_openai()
    resp = client.embeddings.create(input=text, model=EMBEDDING_MODEL)
    return resp.data[0].embedding


# ---------------------------------------------------------------------------
# Upsert helpers
# ---------------------------------------------------------------------------

def embed_outage(outage: dict) -> str:
    """Embed an outage record into outage_history. Returns point ID."""
    text = (
        f"{outage.get('area_name', '')} {outage.get('outage_type', '')} "
        f"{outage.get('reason', '')} {outage.get('status', '')} "
        f"{outage.get('source', '')}"
    )
    vector = embed_text(text)
    point_id = str(uuid.uuid4())
    _get_qdrant().upsert(
        collection_name="outage_history",
        points=[
            PointStruct(
                id=point_id,
                vector=vector,
                payload={
                    "area_name": outage.get("area_name"),
                    "outage_type": outage.get("outage_type"),
                    "reason": outage.get("reason"),
                    "status": outage.get("status"),
                    "start_time": str(outage.get("start_time", "")),
                    "end_time": str(outage.get("end_time", "")),
                    "source": outage.get("source"),
                    "severity": outage.get("severity", 1),
                },
            )
        ],
    )
    return point_id


def embed_call(call: dict) -> str:
    """Embed a call log into call_memory. Returns point ID."""
    text = (
        f"{call.get('caller_area', '')} {call.get('user_message', '')} "
        f"{call.get('ai_response', '')}"
    )
    vector = embed_text(text)
    point_id = str(uuid.uuid4())
    _get_qdrant().upsert(
        collection_name="call_memory",
        points=[
            PointStruct(
                id=point_id,
                vector=vector,
                payload={
                    "caller_area": call.get("caller_area"),
                    "user_message": call.get("user_message"),
                    "ai_response": call.get("ai_response"),
                    "outage_found": call.get("outage_found"),
                    "diagnosis_type": call.get("diagnosis_type"),
                },
            )
        ],
    )
    return point_id


def embed_knowledge(text: str, metadata: dict | None = None) -> str:
    """Embed a BESCOM knowledge chunk into bescom_knowledge."""
    vector = embed_text(text)
    point_id = str(uuid.uuid4())
    payload = {"content": text}
    if metadata:
        payload.update(metadata)
    _get_qdrant().upsert(
        collection_name="bescom_knowledge",
        points=[PointStruct(id=point_id, vector=vector, payload=payload)],
    )
    return point_id


def embed_crowd_report(report: dict) -> str:
    """Embed a crowd report into crowd_reports collection."""
    text = f"{report.get('area_name', '')} {report.get('description', '')}"
    vector = embed_text(text)
    point_id = str(uuid.uuid4())
    _get_qdrant().upsert(
        collection_name="crowd_reports",
        points=[
            PointStruct(
                id=point_id,
                vector=vector,
                payload={
                    "area_name": report.get("area_name"),
                    "description": report.get("description"),
                    "report_source": report.get("report_source"),
                    "created_at": str(report.get("created_at", "")),
                },
            )
        ],
    )
    return point_id


# ---------------------------------------------------------------------------
# Search helpers
# ---------------------------------------------------------------------------

def search_similar_outages(query: str, limit: int = 5) -> list[dict]:
    """Semantic search in outage_history."""
    vector = embed_text(query)
    results = _get_qdrant().search(
        collection_name="outage_history",
        query_vector=vector,
        limit=limit,
    )
    return [
        {"score": r.score, **r.payload}
        for r in results
    ]


def search_call_history(query: str, limit: int = 3) -> list[dict]:
    """Semantic search in call_memory."""
    vector = embed_text(query)
    results = _get_qdrant().search(
        collection_name="call_memory",
        query_vector=vector,
        limit=limit,
    )
    return [
        {"score": r.score, **r.payload}
        for r in results
    ]


def search_knowledge(query: str, limit: int = 3) -> list[dict]:
    """RAG search in bescom_knowledge."""
    vector = embed_text(query)
    results = _get_qdrant().search(
        collection_name="bescom_knowledge",
        query_vector=vector,
        limit=limit,
    )
    return [
        {"score": r.score, **r.payload}
        for r in results
    ]


def search_crowd_reports(query: str, limit: int = 5) -> list[dict]:
    """Semantic search in crowd_reports."""
    vector = embed_text(query)
    results = _get_qdrant().search(
        collection_name="crowd_reports",
        query_vector=vector,
        limit=limit,
    )
    return [
        {"score": r.score, **r.payload}
        for r in results
    ]
