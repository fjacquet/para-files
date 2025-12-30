"""Learning module for improving classification accuracy.

This module provides tools for tracking user feedback and extracting
patterns from corrections to improve the classification system over time.
"""

from __future__ import annotations

from para_files.learning.feedback_tracker import CorrectionRecord, FeedbackTracker
from para_files.learning.pattern_extractor import PatternExtractor, PatternSuggestion


__all__ = [
    "CorrectionRecord",
    "FeedbackTracker",
    "PatternExtractor",
    "PatternSuggestion",
]
