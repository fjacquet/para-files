---
title: LLM Fallback Configuration
layout: default
parent: Configuration
nav_order: 6
---

# LLM Fallback Configuration

Optionally enable AI-powered classification for ambiguous files.

## What Is LLM Fallback?

LLM (Large Language Model) Fallback is the last classification signal (Signal 5).

If no other signals match confidently, para-files can ask an AI model to classify the file.

```
Signal 1: Validated DB → No match
Signal 2: Rules → No match
Signal 3: Domain KB → No match
Signal 4: Semantic Router → No match
Signal 5: LLM Fallback ← Asks AI model
```

## Disabled by Default

```yaml
config:
  llm:
    enabled: false  # Default
```

LLM fallback is optional and disabled by default because it requires:
- A running LLM server (e.g., Ollama)
- Extra processing time
- Internet connectivity (for online models)

## Enable LLM Fallback

### Step 1: Start LLM Server

Using Ollama (recommended):

```bash
# Install Ollama from ollama.ai
# Then start the server:
ollama run qwen2.5:1.5b

# Leaves Ollama running at http://localhost:11434
```

### Step 2: Configure para-files

```bash
# Via environment variables:
export PARA_FILES_LLM_ENABLED=true
export PARA_FILES_LLM_API_BASE=http://localhost:11434

# Or in .env file:
# PARA_FILES_LLM_ENABLED=true
# PARA_FILES_LLM_API_BASE=http://localhost:11434

# Or in YAML config:
config:
  llm:
    enabled: true
    api_base: "http://localhost:11434"
```

### Step 3: Verify

```bash
uv run para-files classify ambiguous_file.pdf

# Should use LLM if other signals don't match
```

## LLM Settings

### LLM_ENABLED

Enable/disable LLM fallback:

```bash
export PARA_FILES_LLM_ENABLED=true
```

Default: `false`

### LLM_MODEL

Which model to use:

```bash
export PARA_FILES_LLM_MODEL=ollama/qwen2.5:1.5b
```

Default: `ollama/qwen2.5:1.5b`

Other options:
- `ollama/mistral` - Faster, less accurate
- `ollama/neural-chat` - Good balance
- `openai/gpt-4` - Online (requires API key)
- `ollama/llama2` - Larger, slower

### LLM_API_BASE

Where the LLM server is running:

```bash
export PARA_FILES_LLM_API_BASE=http://localhost:11434
```

Default: `null` (disabled)

Examples:
- `http://localhost:11434` - Local Ollama
- `http://192.168.1.100:11434` - Remote machine
- `https://api.openai.com` - OpenAI (requires API key)

### LLM_CONFIDENCE_THRESHOLD

Minimum confidence for LLM classifications:

```bash
export PARA_FILES_LLM_CONFIDENCE_THRESHOLD=0.6
```

Default: `0.6` (60%)

Lower values = more matches, higher false positive rate.

## Full YAML Example

```yaml
config:
  llm:
    enabled: true
    model: "ollama/qwen2.5:1.5b"
    api_base: "http://localhost:11434"
    confidence_threshold: 0.6
```

## Performance Impact

**Without LLM:** Fast (uses embeddings)
- Embedding matching: 10-15ms

**With LLM:** Slower (only for unmatched files)
- Local model (Ollama): +500ms-2s per file
- Online model (OpenAI): +1-3s per file

LLM only runs when other signals don't match, so impact varies.

## When to Use LLM Fallback

**Good for:**
- Ambiguous documents that don't fit patterns
- Learning what documents are about
- Complex classification rules

**Not needed when:**
- You have good utterances and issuers
- You're willing to manually fix misclassifications
- Speed is critical

## Troubleshooting

**"Connection refused" error?**

```bash
# Make sure Ollama is running:
ollama run qwen2.5:1.5b

# Check API base URL:
export PARA_FILES_LLM_API_BASE=http://localhost:11434
```

**LLM not being used?**

```bash
# Verify it's enabled:
uv run para-files config --show

# Check PARA_FILES_LLM_ENABLED=true
```

**LLM too slow?**

```bash
# Use smaller model:
export PARA_FILES_LLM_MODEL=ollama/mistral

# Or disable and improve utterances instead
export PARA_FILES_LLM_ENABLED=false
```

## Related

- **[Configuration Overview](overview.md)** - All settings
- **[Architecture: Signal 5](../architecture/signal-5-llm.md)** - LLM details
- **[Task: Enable LLM](../tasks/enable-llm-fallback.md)** - Setup guide
