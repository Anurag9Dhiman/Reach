# Reach paper

`par_paper.tex` is the Reach systems paper. Last updated 2026-10-07 to
replace the Webots-era physical-simulation story with a MuJoCo Franka Panda
one (see `mujoco/`), re-pointing Sections III.F / V.B / V.D / VI / VII and
Table II at the new backend, dropping the retired physically-real gantry
subsection (III.G) along with its vision-guided-button-choice narrative,
and adding a cross-simulator-cross-validation framing to the hardware-in-
the-loop finding. The 31-experiment evaluation suite (`experiments/`)
remains the empirical core; E16, E17, and E18 were re-run against MuJoCo
and their result files updated.

Reconstructed from the originally-circulated `Reach_Project.pdf` (dated
2026-09-24, from an Overleaf project) rather than edited from that project's
live source - the live Overleaf `.tex` wasn't available locally, and a
separate local copy that surfaced during this update turned out to belong to
a different, unrelated in-progress revision (a different 24-experiment
suite, not this repo's 33-experiment plan), so it was deliberately not used.
If you have edit access to the original Overleaf project, treat this file as
the update to paste in, not as a replacement source of truth for anything
*not* called out above as changed - the Introduction, Related Work, and
Sections III.A-III.F are carried over from the original wording.

The bibliography is inlined directly (`\begin{thebibliography}`) rather than
via a `.bib` + `bibtex` pass, for the same reason: no `.bib` file matching
this paper's actual 21 references was available locally.

## Recompiling

No system LaTeX install was available in the environment this was written
in (installing one needs an interactive `sudo` password this session
couldn't supply), so it was compiled with
[tectonic](https://tectonic-typesetting.github.io/) instead, which needs no
system TeX install:

```bash
brew install tectonic   # formula, not a cask - no sudo needed
cd paper
tectonic par_paper.tex
```

This produced `par_paper.pdf` (7 pages) cleanly - no errors, only routine
`Overfull`/`Underfull \hbox` cosmetic warnings from the table layout. A
standard `pdflatex`/Overleaf toolchain should compile it identically, since
nothing in the source is tectonic-specific.
