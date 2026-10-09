# Companion website — instructions for Claude

This repository publishes https://submarrin.github.io/non-euclidean/ (GitHub Pages, branch `main`, root).

## The site is generated from the thesis
- `index.html` is **generated**. Do not edit it by hand.
- Source of truth for chapter text and bibliography: the private thesis repo
  `submarrin/master_thesis_non-euclidean`. Which thesis files feed which tab is set in
  `CHAPTERS` in `tools/build_site.py` (now: ch. 2 ← `ch02_history_iter1.tex` + `references_iter1.bib`).
- Page design, tabs, figures (SVG), portraits, placeholders: `src/page.html`.
- Site-only wording that intentionally differs from the thesis: `tools/overrides.json` (keep it short).
- Build: `python3 tools/build_site.py --thesis <path to thesis repo>`.

## Rule: every change in the thesis must appear on the site
- A GitHub Action in the thesis repo (`.github/workflows/update-site.yml`) rebuilds and pushes
  this site on every push to the thesis `main` branch.
- If you change the thesis without that Action (or it fails), rebuild and push this repo yourself.
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
