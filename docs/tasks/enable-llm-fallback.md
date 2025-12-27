---
title: Enable LLM Fallback
layout: default
parent: Tasks
nav_order: 13
---

# Enable LLM Fallback Classification

Set up optional AI-powered classification for ambiguous files.

## Prerequisites

- Ollama installed (<https://ollama.ai>)
- Model downloaded: `ollama run qwen2.5:1.5b`

## Step 1: Start LLM Server

```bash
# Start Ollama (leave running)
ollama run qwen2.5:1.5b

# Leaves server at http://localhost:11434
```

## Step 2: Configure para-files

Option A: Environment variables

```bash
export PARA_FILES_LLM_ENABLED=true
export PARA_FILES_LLM_API_BASE=http://localhost:11434
```

Option B: .env file

```bash
PARA_FILES_LLM_ENABLED=true
PARA_FILES_LLM_API_BASE=http://localhost:11434
```

Option C: YAML config

```yaml
config:
  llm:
    enabled: true
    api_base: "http://localhost:11434"
```

## Step 3: Verify

```bash
# Check it's configured
uv run para-files config --show

# PARA_FILES_LLM_ENABLED should be true
```

## Step 4: Test

```bash
# Classify ambiguous file
uv run para-files classify unclear_document.pdf

# If other signals don't match, LLM will be asked
```

## Troubleshooting

**"Connection refused"?**

```bash
# Make sure Ollama is running
ollama run qwen2.5:1.5b

# Check endpoint
curl http://localhost:11434/api/tags
```

**LLM not being used?**

```bash
# Check it's enabled
uv run para-files config --show

# Use verbose to see if LLM was tried
uv run para-files classify file.pdf -v
```

## Performance Notes

- First classification: ~1-3 seconds (LLM loads)
- Subsequent: ~500ms-2s per file
- Only runs when other signals don't match

## Alternative: Different Model

```bash
# Use smaller, faster model
ollama run mistral

# Configure para-files
export PARA_FILES_LLM_MODEL=ollama/mistral
```

Slower models (more accurate):

- `llama2` - Large, accurate, slow
- `neural-chat` - Good balance

## When to Use LLM

**Good for:**

- Truly ambiguous documents
- Learning what files are about
- Complex classification

**Not needed for:**

- Most daily use
- If you have good utterances/issuers
- Time-sensitive classification

## Related

- **[Configuration](../configuration/llm-fallback.md)** - Full LLM setup
- **[Architecture: Signal 5](../architecture/signal-5-llm.md)** - LLM details
