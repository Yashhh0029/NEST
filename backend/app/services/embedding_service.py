import hashlib
import logging
import math
import re
from typing import Any, List, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

STOP_WORDS = {
    "a", "an", "the", "in", "on", "at", "to", "for", "of", "and", "or", "is",
    "are", "was", "were", "who", "can", "with", "from", "by", "as", "about",
    "i", "my", "me", "you", "your", "it", "this", "that", "role", "profile",
    "helper", "newcomer", "headline", "bio", "location", "skills",
}

DOMAIN_CLUSTERS = {
    "concept_housing": {
        "accommodation", "housing", "pg", "pgs", "rent", "rental", "room",
        "rooms", "flat", "flats", "apartment", "hostel", "stay", "paying",
        "guest", "bachelor", "broker", "deposit", "lease",
    },
    "concept_transport": {
        "transport", "transit", "bus", "buses", "metro", "cab", "cabs",
        "auto", "commute", "commuting", "travel", "route", "railway",
        "station", "airport", "traffic",
    },
    "concept_food": {
        "food", "tiffin", "mess", "meal", "meals", "groceries", "restaurant",
        "veg", "vegetarian", "nonveg", "kitchen", "dining", "cook", "cooking",
    },
    "concept_health": {
        "healthcare", "medical", "doctor", "clinic", "hospital", "pharmacy",
        "medicine", "emergency", "chemist",
    },
    "concept_tech": {
        "tech", "technology", "programming", "software", "python", "machine",
        "learning", "ml", "ai", "engineer", "developer", "coding", "mentor",
        "mentoring", "data", "fullstack", "backend", "frontend",
    },
    "concept_guidance": {
        "guide", "guiding", "guidance", "help", "helping", "navigating",
        "settling", "advice", "local", "neighborhood", "area", "city",
    },
}

WORD_TO_CLUSTERS = {}
for c_name, words in DOMAIN_CLUSTERS.items():
    for w in words:
        WORD_TO_CLUSTERS.setdefault(w, set()).add(c_name)


class VectorResult(list):
    """List subclass providing .tolist() for sentence-transformers drop-in compatibility."""

    def tolist(self) -> List[float]:
        return list(self)


class LightweightEmbeddingModel:
    """
    High-performance, zero-RAM, CPU-native semantic text embedding model.
    Produces deterministic, unit-normalized 384-dimensional dense vectors
    compatible with pgvector without requiring PyTorch, CUDA, or Transformers.
    """

    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    def encode(self, texts: Any, normalize_embeddings: bool = True) -> Any:
        if isinstance(texts, str):
            return VectorResult(self._embed_single(texts, normalize_embeddings))
        elif isinstance(texts, (list, tuple)):
            return [VectorResult(self._embed_single(t, normalize_embeddings)) for t in texts]
        raise TypeError(f"Expected str or list of str, got {type(texts)}")

    def _embed_single(self, text: str, normalize: bool = True) -> List[float]:
        text_lower = text.lower().strip()
        if not text_lower:
            return [0.0] * self.dimension

        vec = [0.0] * self.dimension
        raw_words = re.findall(r"\b[a-z0-9]+\b", text_lower)
        words = [w for w in raw_words if w not in STOP_WORDS]
        if not words:
            words = raw_words

        # Expand domain concept clusters for high-level semantic alignment
        expanded = list(words)
        for w in words:
            if w in WORD_TO_CLUSTERS:
                expanded.extend(WORD_TO_CLUSTERS[w])

        counts = {}
        for item in expanded:
            counts[item] = counts.get(item, 0) + 1

        for token, count in counts.items():
            weight = math.log1p(count) * (2.5 if token.startswith("concept_") else 1.0)
            # Hash to multiple buckets across 384 dimensions
            for seed in range(6):
                h = int(hashlib.sha256(f"{seed}:{token}".encode("utf-8")).hexdigest(), 16)
                idx = h % self.dimension
                sign = 1.0 if ((h >> 16) & 1) else -1.0
                vec[idx] += sign * weight

            # Subword 3-grams for morphological resilience
            if len(token) >= 3 and not token.startswith("concept_"):
                for i in range(len(token) - 2):
                    gram = token[i:i + 3]
                    gh = int(hashlib.md5(gram.encode("utf-8")).hexdigest(), 16)
                    vec[gh % self.dimension] += (1.0 if ((gh >> 16) & 1) else -1.0) * weight * 0.3

        if normalize:
            norm = math.sqrt(sum(x * x for x in vec))
            if norm > 0:
                vec = [x / norm for x in vec]
            else:
                vec = [0.0] * self.dimension

        return vec


class EmbeddingService:
    """
    Embedding service managing 384-dimensional vector representations.
    Uses LightweightEmbeddingModel in production for low memory usage and high throughput.
    """

    _instance: Optional["EmbeddingService"] = None
    _model: Optional[Any] = None

    def __new__(cls) -> "EmbeddingService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def model_name(self) -> str:
        return settings.EMBEDDING_MODEL

    @property
    def dimension(self) -> int:
        return settings.EMBEDDING_DIMENSION

    def _get_model(self) -> Any:
        if self._model is None:
            logger.info("Initializing lightweight CPU embedding model for '%s'...", self.model_name)
            self._model = LightweightEmbeddingModel(dimension=self.dimension)
        return self._model

    def embed_text(self, text: str) -> List[float]:
        """
        Generate a normalized 384-dimensional dense semantic embedding for input text.
        """
        clean_text = text.strip()
        if not clean_text:
            raise ValueError("Cannot generate embedding for empty text.")

        model = self._get_model()
        try:
            vector = model.encode(clean_text, normalize_embeddings=True)
            embedding_list = vector.tolist() if hasattr(vector, "tolist") else list(vector)
        except Exception as exc:
            logger.error("Embedding generation failed for text '%s...': %s", clean_text[:50], exc)
            raise RuntimeError(f"Embedding generation error: {exc}") from exc

        if len(embedding_list) != self.dimension:
            raise ValueError(
                f"Embedding dimension mismatch: expected {self.dimension}, got {len(embedding_list)}"
            )

        return embedding_list

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Batch generate embeddings for multiple texts.
        """
        clean_texts = [t.strip() for t in texts if t.strip()]
        if not clean_texts:
            return []

        model = self._get_model()
        try:
            vectors = model.encode(clean_texts, normalize_embeddings=True)
            return [v.tolist() if hasattr(v, "tolist") else list(v) for v in vectors]
        except Exception as exc:
            logger.error("Batch embedding generation failed: %s", exc)
            raise RuntimeError(f"Batch embedding error: {exc}") from exc

    @staticmethod
    def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
        """
        Compute cosine similarity between two normalized vectors via dot product.
        """
        if len(vec_a) != len(vec_b):
            raise ValueError("Vectors must have the same length.")
        return float(sum(a * b for a, b in zip(vec_a, vec_b)))


embedding_service = EmbeddingService()


def get_embedding_service() -> EmbeddingService:
    return embedding_service
