"""PARA Files - sorts personal files into a PARA folder tree.

It reads a YAML tree of destination folders, files each document by rules, issuers and
content, asks a model only when those leave doubt, and can undo every run.
"""

from __future__ import annotations


__version__ = "1.9"
__author__ = "Your Name"
__all__ = ["__version__"]
