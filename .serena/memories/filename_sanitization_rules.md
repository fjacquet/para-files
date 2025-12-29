# Filename Sanitization Rules

## Invalid Characters

All paths and filenames must be filesystem-safe. The following characters are invalid:
- `,` (comma) - can cause issues in some systems
- `#` (hash) - can cause URL encoding issues
- `"` (double quote) - invalid on Windows
- `*` (asterisk) - invalid on Windows
- `:` (colon) - invalid on Windows, used for drive letters
- `<` (less than) - invalid on Windows
- `>` (greater than) - invalid on Windows
- `?` (question mark) - invalid on Windows
- `/` (forward slash) - path separator on Unix
- `\` (backslash) - path separator on Windows
- `|` (pipe) - invalid on Windows

## Centralized Utilities

Use these functions from `para_files.utils.filename_sanitizer`:

### sanitize_filename()
For filenames (replaces invalid chars + spaces with underscore):
```python
sanitize_filename("Hello: World#1")  # → "Hello_World_1"
sanitize_filename("file*.txt")  # → "file_.txt"
```

### sanitize_path_component()
For path components (preserves spaces, replaces `&` with 'et' for French):
```python
sanitize_path_component("Arts : généralités")  # → "Arts - généralités"
sanitize_path_component("Art & Design")  # → "Art et Design"
```

## Files Using Sanitization

- `src/para_files/classifiers/book_detector.py` - `sanitize_title()`
- `src/para_files/taxonomies/models.py` - `_make_short_name()`, `_make_folder_name()`
- `src/para_files/utils/geolocation.py` - `LocationInfo.folder_name`
