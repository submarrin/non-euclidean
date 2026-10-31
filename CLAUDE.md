# Companion website — instructions for Claude

This repository publishes https://submarrin.github.io/non-euclidean/ (GitHub Pages, branch `main`, root).

## The site is generated from the thesis
- `index.html` is **generated**. Do not edit it by hand.
- Source of truth for chapter text and bibliography: the private thesis repo
  `submarrin/master_thesis_non-euclidean`. Which thesis files feed which tab is set in
  `CHAPTERS` in `tools/build_site.py` (now: ch. 2 ← `ch02_history_iter1.tex` + `references_iter1.bib`).
- Page design, tabs, figures (SVG), portraits, placeholders: `src/page.html`.
- Site-only wording that intentionally differs from the thesis: `tools/overrides.json` (keep it short).
- Local preview build: `python3 tools/build_site.py --thesis <path to thesis repo>` (do not commit the result).

## Rule: only the pipeline publishes index.html
- **Never commit `index.html` yourself**, not even after a local build: a local build may use an old
  copy of the thesis and silently undo newer text (this happened on 2026-10-16).
  Commit only sources (`src/`, `tools/`, `img/`, …) and push; the pipeline builds and publishes.
- Both pipelines run `tools/publish.sh`, which always builds from the **current thesis `main`**
  and, if the push is rejected because someone else published first, refreshes both repos and rebuilds.
  - Thesis repo, `.github/workflows/update-site.yml`: on every push to the thesis `main`.
  - This repo, `.github/workflows/build.yml`: on every push to this repo's `main`, daily, and by hand
    (Actions → Build and check website → Run workflow).
- Version stamp: every page carries `<meta name="thesis-commit" content="<sha>">` and a footer line
  "Built from thesis version <sha> (<date>)". The `check-live` job compares the live page with the
  thesis `main` and fails (GitHub emails the owner) if they differ for 15 minutes.
- Local builds are previews only. If the thesis has uncommitted changes, the build warns and the
  stamp says "with uncommitted local changes".
- Only supervisor-approved files are listed in `CHAPTERS`. Add a chapter there only when the author says it is approved.

## Figures
Figures are converted from the thesis TikZ at build time by `tools/tikz2svg.py` (scopes, paths, plot
coordinates, arcs, circles, nodes, foreach, clip, fills). So a changed figure in the thesis updates the site
automatically. If a figure uses TikZ the converter does not support, the build warns and falls back to a
hand-drawn SVG in `src/page.html` (`FIGS`), guarded by a hash in `tools/figures.lock.json`; without a
fallback the page shows a short "being drawn" note. Prefer extending the converter over hand drawings.

## Content rules (from the author)
- Use only material from the thesis files. Citations exactly as in the thesis (biblatex alphabetic labels).
- No historical facts that are not in the thesis; put ideas without a source in `TODO.md` under "To verify".
- Portraits: public domain, with a credit line (Bolyai: CC BY-SA 3.0, kept with attribution).
- Images that are on the website but not in the thesis PDF go in the right-hand portrait column, at portrait size
  (`PORTRAITS`, or `SITE_FIGS` for drawings beside a paragraph), never as full-width figures in the text.
