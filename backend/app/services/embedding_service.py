import logging
from typing import List, Optional
from sentence_transformers import SentenceTransformer
from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Singleton embedding service managing sentence-transformers model instance.
    Loads all-MiniLM-L6-v2 once into memory and validates 384-dimensional vector output.
    """

    _instance: Optional["EmbeddingService"] = None
    _model: Optional[SentenceTransformer] = None

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

    def _get_model(self) -> SentenceTransformer:
        if self._model is None:
            logger.info("Loading embedding model '%s'...", self.model_name)
            try:
                # First try local cache to avoid external network calls
                self._model = SentenceTransformer(self.model_name, local_files_only=True)
            except Exception:
                try:
                    self._model = SentenceTransformer(self.model_name)
                except Exception as exc:
                    logger.error("Failed to load sentence-transformers model '%s': %s", self.model_name, exc)
                    raise RuntimeError(f"Embedding model initialization failed: {exc}") from exc
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
            embedding_list = vector.tolist()
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
            return [v.tolist() for v in vectors]
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
