# Khaos Hub Library

The Library is a private, local index for saved references. It does not read browsing history, sign in to browser accounts, fetch bookmarked pages, or copy page contents. Its database stays at `~/.local/share/khaos-hub/library.sqlite3` with owner-only permissions.

## Browser import

1. Open **Library** and choose **Find browser bookmarks**.
2. Review the per-browser profile counts and the estimate for new links, existing matches, and duplicates. The preview contains counts only.
3. Choose **Import and merge duplicates** to proceed. Originals remain in their browser profiles.

The importer reads local Brave, Chromium, Chrome, Vivaldi, Edge, and Firefox bookmark stores when present. Firefox data is read through SQLite's snapshot backup into a temporary directory. Import is one database transaction; a verified owner-only database backup is made before it changes stored items. A failed or expired preview cannot be imported.

Links are matched after normalizing scheme/host case, default ports, and an empty root path. Query strings and fragments are preserved. Existing Library titles, notes, and tags stay as authored; imported browser/profile/folder/title provenance is merged into the source details. Reading-list labels are recognized only when present in a browser bookmark tree or folder. No dedicated reading-list items were present in the workstation profiles inspected on 2026-10-23.

JSON export/import is available for moving this local index. Imports are size-limited, validated as `http`/`https` references, and applied in one transaction. Never place credentials or private access URLs in the Library.
