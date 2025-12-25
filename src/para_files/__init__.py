"""PARA Files - Intelligent file classification using MLX-powered semantic routing.

This package implements the PARA method (Projects, Areas, Resources, Archives)
with a deterministic embedding-based classification pipeline for personal files
and work emails on macOS.
"""

from para_files.config import Config
from para_files.main import cli, main
from para_files.pipeline import ClassificationPipeline
from para_files.types import ClassificationResult, ClassificationSource, Confidence


__version__ = "0.1.0"
__author__ = "Your Name"
__all__ = [
    "ClassificationPipeline",
    "ClassificationResult",
    "ClassificationSource",
    "Confidence",
    "Config",
    "__version__",
    "cli",
    "main",
]
