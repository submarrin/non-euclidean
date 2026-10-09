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
TikZ cannot be converted automatically. Each figure label has a hand-drawn SVG function in
`src/page.html` (`FIGS`), made from the TikZ coordinates. `tools/figures.lock.json` stores a hash of the
TikZ code each drawing matches. When a thesis figure changes, the build warns and the page shows a note
under that figure. Then: redraw it in `src/page.html` from the new TikZ, rebuild with `--accept-figures`, commit.

## Content rules (from the author)
- Use only material from the thesis files. Citations exactly as in the thesis (biblatex alphabetic labels).
- No historical facts that are not in the thesis; put ideas without a source in `TODO.md` under "To verify".
- Portraits: public domain, with a credit line (Bolyai: CC BY-SA 3.0, kept with attribution).
