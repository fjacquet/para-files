"""Encoders for semantic routing."""

from para_files.encoders.ollama_encoder import OllamaEncoder


# Backward compatibility alias
MLXEncoder = OllamaEncoder

__all__ = ["MLXEncoder", "OllamaEncoder"]
