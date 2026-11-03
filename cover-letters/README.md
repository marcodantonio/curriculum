# Company cover letters

One monochrome, single-column LaTeX layout, with justified paragraphs and a
one-page compilation guard. Each application produces **both Italian and English**.
The sender's name and contacts come from `content/common/personal.tex`; CV layouts
and content remain independent. No external AI API, credentials or new TeX packages
beyond the existing compiler environment are needed.

## Create a company draft

From the repository root:

```bash
python3 scripts/cover-letter.py init company-slug --company "Company name"
```

This creates `cover-letters/applications/company-slug/application.json` without
reusing an existing company directory. The starter paragraphs come from `defaults.json`, based on
the approved CV. They are editable writing suggestions, not automatic company
research or automatically synchronized professional history.

First complete the shared `position` brief in `application.json`:

- `title`: the exact advertised role, used in both letters' subject and opening.
- `url`: the source job posting URL.
- `location`: location and working arrangement stated in the posting.
- `requirements`: the relevant tasks and requirements from the posting.
- `fit`: entries with `requirement`, `evidence` and `contribution`, connecting a
  listed requirement to verified experience and a concrete contribution.

Then edit both `languages.it` and `languages.en`:

- `recipient` and `salutation`: the person or hiring team, if known.
- `motivation`: a specific reason to apply, tied to a requirement of the role.
- `paragraphs`: one to six paragraphs selecting relevant evidence from your work.
- `contribution`: a persuasive, role-specific paragraph explaining where you can
  be useful. It is included in the letter after the supporting experience.
- `closing`: the closing paragraph, before the localized sign-off.

`company` is shared. Write plain text, including accents and characters such as
`&`, `%` or `_`; the generator escapes LaTeX syntax. Put each paragraph in a
separate array entry. Do not put TeX commands in the JSON.

Set `ready` to `true` only after reviewing both languages. Missing position briefs,
empty motivations or contributions, missing fields or missing translations prevent
compilation. The generator checks structure, required text and requirement links;
the author must verify factual accuracy, evidence and relevance. It does not
automatically research a company or infer unverified qualifications.
It does not send applications or contact companies.

## Build

```bash
make cover-letter APPLICATION=company-slug
make cover-letters
make all
```

- `cover-letter` builds the selected company's IT/EN pair.
- `cover-letters` builds every ready application; drafts (`ready: false`) are skipped.
- `all` builds all four CV variants and every ready cover letter.

The CLI equivalent is `python3 scripts/cover-letter.py build company-slug`.
Files are exported only after both language compilations succeed; a compiler
failure preserves previous exported PDFs.

```text
cover-letters/applications/company-slug/     # editable public company dossier
   application.json                        # position brief and IT/EN letter copy
   research.md                             # optional sources and review notes
build/cover-letters/company-slug/             # generated TeX, logs and intermediates
dist/cover-letters/company-slug/
   cover-letter-it.pdf
   cover-letter-en.pdf
```

Edit the JSON, not generated `.tex` files: rebuilding replaces the latter. Existing
CV editor previews are preserved. All company inputs, job briefs, research notes
and PDF exports are public and versioned in Git. There are no company-specific
publication exceptions; new applications follow the same rule. `make clean` removes
compiled outputs and cover-letter intermediates, preserving application JSON and
CV editor previews. Do not use it when you still need exported PDFs.

## Layout preview and verification

```bash
python3 scripts/cover-letter.py --applications-dir cover-letters/examples build example
python3 -m unittest discover -s tests -v
```

The example is explicitly a layout demonstration, not an actual application.
CI compiles the example, all CV variants and every ready company application,
and uploads the PDFs as workflow artifacts. Draft application sources are also
public but remain uncompiled until marked ready. Examples follow the same
company-folder structure.

Legacy flat `applications/company-slug.json` files are rejected explicitly rather
than silently skipped. Move them into a company folder and complete the position
brief and contribution fields before building. Sizeless has already been migrated.

The CLI also accepts `--applications-dir`, `--output-dir` and `--work-dir` before
the subcommand for isolated local checks. Keep them in distinct directories.
Compiler selection follows the CV convention: existing `latexmk`/LuaLaTeX first,
then `CV_TECTONIC_BIN`, `tectonic` on PATH, or the bundled macOS compiler.

## Maintenance

Write for the role, not a generic biography: company need, relevant evidence,
concrete contribution. Use confident, specific language without invented metrics,
domain expertise or availability. Keep sources and gaps in the company dossier,
not in the letter. The position brief is writing context, not a block copied into
the PDF; only its role title and the authored contribution appear automatically.

Keep `defaults.json` consistent with verified CV facts when changing experience
or projects. Existing applications retain their company-specific edits and must
be reviewed individually. Keep `template.tex` as the only letter layout; no
single/double-column variants are created for letters.
