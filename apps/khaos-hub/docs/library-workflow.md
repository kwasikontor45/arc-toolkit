# Khaos Hub Library

The Library is a private, local index for saved references. It does not read browsing history, sign in to browser accounts, fetch bookmarked pages, or copy page contents. Its database stays at `~/.local/share/khaos-hub/library.sqlite3` with owner-only permissions.

## Browser import

1. Open **Library** and choose **Find browser bookmarks**.
2. Review the per-browser profile counts and the estimate for new links, existing matches, and duplicates. The preview contains counts only.
3. Choose **Import and merge duplicates** to proceed. Originals remain in their browser profiles.

The importer reads local Brave, Chromium, Chrome, Vivaldi, Edge, and Firefox bookmark stores when present. Firefox data is read through SQLite's snapshot backup into a temporary directory. Import is one database transaction; a verified owner-only database backup is made before it changes stored items. A failed or expired preview cannot be imported.

Links are matched after normalizing scheme/host case, default ports, and an empty root path. Query strings and fragments are preserved. Existing Library titles, notes, and tags stay as authored; imported browser/profile/folder/title provenance is merged into the source details. Reading-list labels are recognized only when present in a browser bookmark tree or folder. No dedicated reading-list items were present in the workstation profiles inspected on 2026-10-23.

JSON export/import is available for moving this local index. Imports are size-limited, validated as `http`/`https` references, and applied in one transaction. Never place credentials or private access URLs in the Library.

The Library renders references in small batches so a large collection does not turn into a long, heavy page. Search and type filters start at the first batch; **Show next** reveals more without losing the current filter.

## Dewey study shelf

The **Dewey study shelf** is a separate, read-only catalog alongside saved web references. Its source is the owner-only file `~/khaos-lab/local-cloud-hub/personal-cabinet/library/dewey-catalog.json`. It contains Dewey subject labels, titles, short descriptions, and paths relative to `~/khaos-lab`; the Hub checks whether each listed source file exists and displays missing paths as unavailable. The browser can copy a path, but the Hub does not open, upload, or serve the referenced document.

Original tutorials remain in their canonical project directories. Do not copy them into the shelf or duplicate generated Notes Site pages, inbox briefing copies, or archived snapshots. Add an item only when it is a durable tutorial, study resource, or operator reference the owner is likely to reuse. Keep credentials, academic submissions, private personal records, session logs, and evidence archives out of the catalog. Update the index by hand after checking the source path and subject; no filesystem crawler is used.

The local Dewey labels are practical browse categories, not a formal library catalog record. They follow the primary subject of each item: 004.6 computer communications, 005.1 software development, 005.4 systems software, 005.5 application software, 005.7 data and databases, 005.8 computer security, 658.478 security management, and 780 music. For the schedule descriptions, use [OCLC's 004–005 Dewey reference](https://www.oclc.org/content/dam/oclc/webdewey/help/000.pdf) and [OCLC's 780 music reference](https://www.oclc.org/content/dam/oclc/webdewey/help/700.pdf).

### Privacy and failure boundary

The catalog endpoint returns approved titles, subject labels, summaries, and local relative paths only; it never returns file contents. It validates the catalog size/schema, rejects symlink escapes and paths outside approved Khaos Lab roots, and fails closed if the index is malformed. Hub binds to `127.0.0.1` and checks the exact Host, Origin, and Fetch Metadata values. This protects against remote exposure and ordinary cross-origin browser requests; loopback HTTP is not per-user authentication, so local processes on the same workstation may still request the metadata. Keep the catalog free of secrets and sensitive personal titles. If Hub becomes multi-user or remotely reachable, replace this boundary with an authenticated per-user transport before exposing the shelf.
