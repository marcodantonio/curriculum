# Marco D'Antonio – LaTeX CV

This repository contains my CV written in LaTeX.

The project is structured to keep content, layout and build logic separated, making it easy to maintain different layouts and languages over time.

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

Examples:

```bash
make all
make list
./scripts/build.sh double-column all
./scripts/build.sh double-column en
./scripts/build.sh single-column it
```

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
