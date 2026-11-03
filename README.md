# Marco D'Antonio – CV and cover letters

This repository generates my LaTeX CV and bilingual company cover letters.
Cover letters use one dedicated single-column layout; see
[cover-letters/README.md](cover-letters/README.md) for the application workflow.
Each company has its own application folder with the job brief, evidence of fit
and tailored IT/EN copy. The advertised role drives the letter's title and opening.

The project is structured to keep content, layout and build logic separated, making it easy to maintain different layouts and languages over time.

The single-column CV uses TeX Gyre Heros throughout, black text, a consistent
hierarchy of font weights and sizes, and a legal notice in the page footer.
It enforces a one-page limit during compilation. The double-column theme remains
available with its existing visual design. Content stays in `content/lang/`,
layout in `themes/`, and the QR is a vector trace of the existing PNG.

Single-column entries use a consistent hierarchy: bold primary title, role or
technical scope on the following line, then the description. Dates stay aligned
with the primary title. Italian and English content describe the same experience
and projects; shared theme components apply to both languages.
Body paragraphs are justified in both themes; dates and the QR retain their
dedicated alignment.
Both headlines use `\CVAge`, calculated from the birth date in
`content/common/personal.tex` and the compiler's date. Rebuild the PDFs to update
the displayed age; already exported PDFs remain unchanged.

## Available

Themes:
- double-column
- single-column

Languages:
- en
- it

## Build

Requirements:
- latexmk
- lualatex (TeX Live / MacTeX / BasicTeX)
- Python 3.9+ for standalone preview synchronization

If `latexmk` is unavailable, the script uses an existing Tectonic executable
(`tectonic` on PATH, `CV_TECTONIC_BIN`, or the copy bundled with ChatGPT on macOS).
Nothing is installed by the build script. Both compiler paths use the same
modular content and theme; the Tectonic path compiles their standalone expansion.

The build script is also compatible with macOS' BSD `find` implementation.

Examples:

```bash
make all
make list
make cover-letters
./scripts/build.sh double-column all
./scripts/build.sh double-column en
./scripts/build.sh single-column it
```

For every CV update, rebuild **all languages and both themes** with `make all`
or `./scripts/build.sh all` before delivery or publication. Targeted commands
are useful for diagnosis only. Review all four PDFs and publish the matching
sources and `dist/` outputs together.
`make all` also builds every ready local cover letter in IT/EN. Company application
data and letter PDFs are ignored by Git; the four CV PDFs remain versioned.

Generated PDFs are placed under:

```text
dist/
├── double-column/
│   ├── cv-en.pdf
│   └── cv-it.pdf
└── single-column/
    ├── cv-en.pdf
    └── cv-it.pdf
```

## Project structure

Main entrypoint is `main.tex`.

Content, themes and build logic are organized as follows:

```text
.
├── main.tex
├── config/build.tex
├── assets/qr-code.png
├── core/
│   ├── packages.tex
│   ├── language-setup.tex
│   └── theme-loader.tex
├── themes/
│   ├── double-column/
│   │   ├── styles.tex
│   │   ├── components.tex
│   │   └── layout.tex
│   └── single-column/
│       ├── styles.tex
│       ├── components.tex
│       └── layout.tex
├── content/
│   ├── common/personal.tex
│   └── lang/
│       ├── en/
│       ├── it/
│       └── _template/
├── scripts/build.sh
├── dist/
└── .github/workflows/build.yml
```

## Language structure

Each language is split into multiple files (experience, education, projects, etc.), so content stays independent from layout.

To add a new language:
1. Copy `content/lang/_template/`
2. Translate the files
3. (Optional) update `core/language-setup.tex` if needed

Build example:

```bash
./scripts/build.sh double-column fr
./scripts/build.sh single-column fr
```

## Themes

Each theme lives under `themes/` and defines its own layout and styles.

To add a new theme:
1. Duplicate an existing theme folder
2. Adjust `styles.tex`, `components.tex` and `layout.tex`

Build example:

```bash
./scripts/build.sh your-theme en
```

## Notes

- double-column is more compact and works well for a one-page CV
- single-column follows more closely the original Word layout (including the QR code)
- outputs are grouped by theme to keep builds organized

## Editable desktop preview

The existing editor source is `build/review-single-column/cv-it.tex`.
Refresh/synchronize it with:

```bash
python3 scripts/sync-preview.py it
```

Each source block is delimited by `CV-BEGIN` / `CV-END` comments. Edit inside
those blocks, keeping the markers intact. Synchronization imports editor changes
into the owning modular files, then refreshes the preview. If the same source was
also edited outside the preview, it fails without overwriting either version.
Edits to modular sources refresh an unchanged preview normally. Build commands
synchronize their previews automatically; editing alone does not update Git's
modular sources until synchronization runs.

`--initialize` is only for first reconciliation, after the existing preview has
been incorporated into the modular sources. It keeps a `.pre-sync.tex` backup.
Do not use it to bypass a conflict.

`make clean` imports pending preview edits before removing generated build and
`dist` files. It preserves `build/review-*` documents, backups and sync state.
The preview is still ignored by Git; the synchronized modular sources are the
versioned source of truth. The four published PDFs live only in
`dist/single-column/` and `dist/double-column/` (IT/EN for each theme).
Use those files for downloads and delivery; do not maintain additional PDF copies
in `output/`. Build intermediates, desktop previews, macOS metadata and any legacy
`output/` directory are ignored by Git. Keep unrelated artwork outside this repository.

## Local verification

```bash
python3 -m unittest discover -s tests -v
bash -n scripts/build.sh
git diff --check
./scripts/build.sh all
```

Tests cover exact round trips, source/editor updates, conflict preservation,
malformed markers, and clean safety in an isolated temporary repository.
