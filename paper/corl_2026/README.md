# Reach paper, CoRL 2026 format

Same content as `paper/par_paper.tex` (the IEEEtran version), reformatted
for the CoRL 2026 submission template. Both are kept so the IEEEtran
version remains available for arXiv/other venues without re-conversion.

## What's here

- `par_paper.tex` - CoRL 2026 source. Loads `corl_2026.sty` (which you
  need to drop in - see below), uses natbib `\citep{}`/`\citet{}` instead
  of IEEEtran `\cite{}`, author block in NeurIPS style, abstract trimmed
  to 6 sentences per the template requirement.
- `example.bib` - BibTeX bibliography (21 entries, same references as the
  IEEEtran version's inline `thebibliography`).
- Figures live one directory up at `../figures/` and are referenced via
  `\graphicspath{{../}}` so the images don't need duplicating.

## What you need to add

The official CoRL 2026 author kit's style file isn't vendored here (it's
not ours to redistribute, and the kit may be updated by the organizers).
Grab the kit from <https://corl.org/> and drop `corl_2026.sty` into this
directory before compiling. The kit also typically includes a BibTeX
style; CoRL's convention is to leave `\bibliographystyle` out of the
source (the sty handles it).

## Compile

Any standard LaTeX toolchain. With tectonic (what we used for the
IEEEtran version):

```bash
cd paper/corl_2026
tectonic par_paper.tex
```

With pdflatex + bibtex:

```bash
cd paper/corl_2026
pdflatex par_paper
bibtex par_paper
pdflatex par_paper
pdflatex par_paper
```

Or on Overleaf: upload the entire `paper/` directory (so `figures/` and
this subdirectory both land under the project root), add `corl_2026.sty`
from the author kit, and build.

## What changed from the IEEEtran version

Pure mechanical conversion - no new scientific claims:
- `\documentclass{IEEEtran}` -> `\documentclass{article}` + `corl_2026.sty`
- `\IEEEauthorblockN{...}` -> NeurIPS-style `\author{Name \\ Affiliation \\ \texttt{email}}`
- `\cite{X}` -> `\citep{X}` or `\citet{X}` depending on whether the
  citation is parenthetical ("as shown~\citep{X}") or textual
  ("\citet{X} shows that...")
- Inline `\begin{thebibliography}{21}` -> external `example.bib` +
  `\bibliography{example}`
- `\section*{Acknowledgments}{...}` -> `\acknowledgments{...}` command
  (CoRL's style auto-suppresses it under the submission option and shows
  it under final/preprint)
- Added `\keywords{...}` after the abstract (CoRL requirement, IEEEtran
  doesn't use it)
- Abstract compressed from ~15 sentences to 6 (CoRL target: 4-6 sentences)
- Four-panel demo figure stacked as 2x2 instead of 1x4 to fit CoRL's
  single-column format

Section numbering, body text, tables, algorithm, TikZ diagram, cross-
references, labels, and bibliography keys all preserved exactly, so edits
made to one version port cleanly to the other.

## Submission vs. camera-ready

- Default (`\usepackage{corl_2026}`) = anonymous initial submission. Author
  block is auto-suppressed by the style, acknowledgments too.
- Camera-ready: switch to `\usepackage[final]{corl_2026}` - author block
  and acknowledgments both become visible.
- Pre-print (arxiv-style, author block visible but no CoRL footer):
  `\usepackage[preprint]{corl_2026}`.
