---
title: Troubleshooting
layout: default
nav_order: 7
has_children: true
---

# Troubleshooting

Solutions for common issues with para-files.

## Common Issues

| Problem | Solution |
|---------|----------|
| Files going to Inbox | [Improve classification accuracy](troubleshooting/files-going-to-inbox.md) |
| Low confidence scores | [Adjust thresholds](troubleshooting/confidence-too-low.md) |
| Slow model download | [Configure caching](troubleshooting/model-download-slow.md) |

## Quick Diagnostics

```bash
# Check configuration
para-files config

# Test a specific file
para-files classify document.pdf --verbose

# Test routing rules
para-files test-route "document_name.pdf"

# View available routes
para-files routes
```

## Getting Help

If you can't find a solution here:

1. Check the [GitHub Issues](https://github.com/fjacquet/para-files/issues)
2. Search existing issues for your problem
3. Open a new issue with:
   - para-files version (`para-files --version`)
   - macOS version
   - Steps to reproduce
   - Expected vs actual behavior
