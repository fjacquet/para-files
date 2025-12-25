"""Signal 4: Semantic router classifier (85% confidence).

Uses MLX embeddings for semantic similarity matching against
predefined category utterances. This is DETERMINISTIC - same
input always produces the same classification.
"""

from __future__ import annotations

from semantic_router import Route as SRRoute
from semantic_router.routers import SemanticRouter

from para_files.classifiers.base import BaseClassifier
from para_files.encoders.mlx_encoder import MLXEncoder
from para_files.types import (
    ClassificationResult,
    ClassificationSource,
    Confidence,
    FileMetadata,
    Route,
)


class SemanticRouterClassifier(BaseClassifier):
    """Signal 4: Semantic similarity using MLX embeddings (85% confidence).

    Uses the semantic-router library with a custom MLX encoder to match
    content against predefined utterances for each category.

    This classifier is DETERMINISTIC: the same input text will always
    produce the same classification result because MLX embeddings are
    reproducible and no randomness is involved.
    """

    def __init__(
        self,
        encoder: MLXEncoder,
        routes: list[Route],
        score_threshold: float = 0.75,
    ) -> None:
        """Initialize with encoder and routes.

        Args:
            encoder: MLX encoder for generating embeddings.
            routes: List of Route objects with utterances.
            score_threshold: Minimum similarity score to accept match.
        """
        self._encoder = encoder
        self._routes = routes
        self._score_threshold = score_threshold
        self._router: SemanticRouter | None = None
        self._route_map: dict[str, Route] = {r.name: r for r in routes}

    @property
    def name(self) -> str:
        """Return classifier name."""
        return "semantic_router"

    @property
    def source(self) -> ClassificationSource:
        """Return classification source."""
        return ClassificationSource.SEMANTIC_ROUTER

    @property
    def default_confidence(self) -> float:
        """Return default confidence (85%)."""
        return 0.85

    def _ensure_router(self) -> SemanticRouter:
        """Lazily build semantic router on first use.

        Returns:
            Configured SemanticRouter instance.
        """
        if self._router is None:
            # Convert our Route objects to semantic-router Route objects
            sr_routes = [
                SRRoute(name=route.name, utterances=route.utterances)
                for route in self._routes
                if route.utterances  # Only include routes with utterances
            ]

            self._router = SemanticRouter(
                encoder=self._encoder,  # type: ignore[arg-type]
                routes=sr_routes,
                auto_sync="local",
            )

        return self._router

    def classify(
        self,
        content: str,
        _metadata: FileMetadata | None = None,
    ) -> ClassificationResult | None:
        """Classify content using semantic similarity.

        Args:
            content: Text content to classify.
            _metadata: File metadata (unused by this classifier).

        Returns:
            ClassificationResult if similarity exceeds threshold, None otherwise.
        """
        if not content.strip():
            return None

        router = self._ensure_router()

        # Get classification from semantic router
        router_result = router(content)

        # Handle case where result is a list (multi-route mode)
        if isinstance(router_result, list):
            if not router_result:
                return None
            choice = router_result[0]
        else:
            choice = router_result

        # Check if we got a match
        route_name = getattr(choice, "name", None)
        if route_name is None:
            return None

        # Find the matching Route to get the pattern
        route = self._route_map.get(route_name)
        if route is None:
            return None

        # Create result with the route's pattern as category
        return ClassificationResult(
            category=route.pattern,
            confidence=Confidence(
                value=self.default_confidence,
                source=self.source,
            ),
            route_name=route_name,
            raw_score=getattr(choice, "similarity_score", None),
        )

    def get_routes_with_utterances(self) -> list[Route]:
        """Return routes that have utterances defined.

        Returns:
            List of Routes with non-empty utterances.
        """
        return [r for r in self._routes if r.utterances]
