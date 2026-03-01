# ADR-002: Apple Silicon (macOS) Only Platform

**Date**: 2024-01-01
**Status**: Accepted
**Deciders**: Frédéric Jacquet

---

## Context

The classification pipeline requires:
1. Fast semantic embedding of file content
2. OCR for scanned PDFs and images
3. A usable CLI that is easy to install

These capabilities could be provided on any platform, but the performance and API characteristics differ significantly across operating systems.

## Decision

**para-files targets macOS on Apple Silicon (M1/M2/M3/M4) exclusively.**

No Linux or Windows support is planned.

## Rationale

### MLX — Apple Neural Engine

[MLX](https://github.com/ml-explore/mlx) is Apple's machine-learning framework optimized for the Unified Memory Architecture of Apple Silicon. It provides:

- **Embedding inference at ~10× the speed** of CPU-only alternatives on the same hardware.
- Zero-copy memory sharing between CPU and GPU — no data transfer overhead.
- First-class Python bindings via `mlx-embedding-models`.

On Linux/Windows the equivalent would be ONNX Runtime or sentence-transformers on CPU/CUDA — viable but slower and requiring separate GPU drivers.

### Vision Framework — Native OCR

Apple's [Vision Framework](https://developer.apple.com/documentation/vision) provides on-device OCR via PyObjC bindings (`pyobjc-framework-Vision`). This:

- Runs entirely offline — no API keys, no per-page costs.
- Achieves high accuracy on bank statements, invoices, and printed documents.
- Handles French, German, English, and other languages out of the box.

Equivalent cross-platform OCR (Tesseract, PaddleOCR) requires additional binary dependencies and produces inferior results on document layouts.

### Target User

The primary user (the author) works exclusively on macOS. Building a cross-platform abstraction layer adds complexity for no current benefit.

## Consequences

- `pyobjc-framework-Vision`, `pyobjc-framework-Quartz`, and `pyobjc-framework-Cocoa` are core dependencies.
- CI/CD runs on `macos-latest` GitHub Actions runners (Apple Silicon).
- The `pyproject.toml` classifier is `Operating System :: MacOS`.
- Users on Linux or Windows cannot install or run this tool.
- Docker-based deployment is not supported or tested.
