#!/usr/bin/env python3
"""
build-master-book-rewrite-images.py <file> — print a markdown/text file's
content with relative image references rewritten to absolute file:// paths,
resolved against the file's own directory.

Used by build-master-book in place of a plain `cat`: once every source file
gets flattened into one big master-book.md, a relative path like
`img/foo.png` that correctly resolved next to its original file breaks,
since it now resolves relative to master-book.md's own location instead.
"""
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

# Matches markdown image syntax ![alt](path) and raw <img src="path">.
MD_IMAGE = re.compile(r'(!\[[^\]]*\]\()([^)]+)(\))')
HTML_IMAGE = re.compile(r'(<img\b[^>]*\bsrc=["\'])([^"\']+)(["\'])')


def _is_relative(path: str) -> bool:
    if path.startswith(("file://", "http://", "https://", "data:", "/")):
        return False
    return bool(urlparse(path).scheme == "")


def _rewrite(content: str, source_dir: Path) -> str:
    def repl(m):
        prefix, path, suffix = m.group(1), m.group(2), m.group(3)
        if not _is_relative(path):
            return m.group(0)
        resolved = (source_dir / path).resolve()
        return f"{prefix}file://{resolved}{suffix}"

    content = MD_IMAGE.sub(repl, content)
    content = HTML_IMAGE.sub(repl, content)
    return content


def main():
    if len(sys.argv) != 2:
        print("Usage: build-master-book-rewrite-images.py <file>", file=sys.stderr)
        sys.exit(1)

    path = Path(sys.argv[1])
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        print(f"error reading {path}: {e}", file=sys.stderr)
        sys.exit(1)

    sys.stdout.write(_rewrite(content, path.resolve().parent))


if __name__ == "__main__":
    main()
