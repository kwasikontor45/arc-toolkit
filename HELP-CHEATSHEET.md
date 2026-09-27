# Arc Help and Reading Cheatsheet

## Find an arc command

| What you need | Command |
|---|---|
| Open the short command map | `arc help` |
| Browse a workspace | `arc help network` |
| Search command names and descriptions | `arc help find backup` |
| Search using more than one word | `arc help find cloud lab` |
| Open the complete reference | `arc help all` |

Available help topics: `daily`, `dev`, `system`, `security`, `logs`, `network`,
`identity`, `reference`, `fixes`, and `shell`. Aliases include `cloud` for `dev`,
`maintenance` for `system`, and `net` for `network`.

## Use the khaos-lab command center

- Press **F1** to open Help.
- Press **Ctrl+F** to focus quick-jump and search available actions.
- Choose a workspace card or sidebar item to browse its actions.
- Confirm-gated actions ask before changing system state; output appears in the console pane.
- Choose **full CLI reference · arc help all** on the Help page for the exhaustive listing.

## Read long Markdown files

Glow now opens files in pager mode by default:

```sh
glow path/to/gameplan.md
```

The toolkit’s Glow launchers also request pager mode. To opt out for a single call,
run `command glow --pager=false path/to/file.md`.
