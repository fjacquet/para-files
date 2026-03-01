"""Encoders for semantic routing."""

from para_files.encoders.mlx_encoder import OllamaEncoder


# Backward compatibility alias
MLXEncoder = OllamaEncoder

__all__ = ["MLXEncoder", "OllamaEncoder"]
