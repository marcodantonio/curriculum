#!/usr/bin/env python3
"""Create and compile bilingual, single-column company cover letters locally."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
APPLICATIONS = ROOT / 'cover-letters' / 'applications'
OUTPUT = ROOT / 'dist' / 'cover-letters'
WORK = ROOT / 'build' / 'cover-letters'
LANGUAGES = ('it', 'en')
FIELDS = {'recipient', 'salutation', 'motivation', 'paragraphs', 'contribution', 'closing'}
ESCAPES = dict(zip('\\&%$#_{}~^', (
    r'\textbackslash{}', r'\&', r'\%', r'\$', r'\#', r'\_',
    r'\{', r'\}', r'\textasciitilde{}', r'\textasciicircum{}')))


def slug_name(slug):
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', slug) or len(slug) > 80:
        raise ValueError('Use a slug of at most 80 lowercase letters, numbers and hyphens.')
    return slug


def text_field(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{name} must be non-empty text.')
    if len(value) > 6000 or any(ord(char) < 32 and char not in '\n\t\r' for char in value):
        raise ValueError(f'{name} contains unsupported characters or is too long.')
    return ' '.join(value.split())


def tex(value):
    return ''.join(ESCAPES.get(char, char) for char in value)


def initialize(slug, company, applications=APPLICATIONS):
    slug_name(slug)
    company = text_field(company, 'company')
    defaults = json.loads((ROOT / 'cover-letters/defaults.json').read_text())
    data = {'company': company, 'ready': False,
            'position': {'title': '', 'url': '', 'location': '', 'requirements': [], 'fit': []},
            'languages': defaults}
    applications.mkdir(parents=True, exist_ok=True)
    if (applications / f'{slug}.json').exists():
        raise FileExistsError(f'Legacy application already exists for {slug}; migrate it first.')
    directory = applications / slug
    # Never reuse an existing company directory or overwrite its documents.
    directory.mkdir()
    target = directory / 'application.json'
    with target.open('x', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write('\n')
    return target


def load_application(path):
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict) or set(data) != {'company', 'ready', 'position', 'languages'}:
        raise ValueError('Expected company, ready, position and languages fields only.')
    if data['ready'] is not True:
        raise ValueError('Complete the application and set ready to true before building.')
    text_field(data['company'], 'company')
    position = data['position']
    if not isinstance(position, dict) or set(position) != {'title', 'url', 'location', 'requirements', 'fit'}:
        raise ValueError('position requires title, url, location, requirements and fit.')
    for name in ('title', 'url', 'location'):
        text_field(position[name], f'position.{name}')
    url = urlsplit(position['url'])
    if url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password:
        raise ValueError('position.url must be an HTTP(S) job posting URL without credentials.')
    requirements = position['requirements']
    if not isinstance(requirements, list) or not requirements:
        raise ValueError('position.requirements must contain the role requirements.')
    for requirement in requirements:
        text_field(requirement, 'position.requirements')
    fit = position['fit']
    if not isinstance(fit, list) or not fit:
        raise ValueError('position.fit must connect requirements, evidence and contribution.')
    for item in fit:
        if not isinstance(item, dict) or set(item) != {'requirement', 'evidence', 'contribution'}:
            raise ValueError('Each fit entry needs requirement, evidence and contribution.')
        for name in item:
            text_field(item[name], f'position.fit.{name}')
        if item['requirement'] not in requirements:
            raise ValueError('Each fit entry must reference a listed requirement.')
    locales = data['languages']
    if not isinstance(locales, dict) or set(locales) != set(LANGUAGES):
        raise ValueError('Provide both it and en language entries.')
    for lang in LANGUAGES:
        entry = locales[lang]
        if not isinstance(entry, dict) or set(entry) != FIELDS:
            raise ValueError(f'{lang}: expected fields {sorted(FIELDS)}.')
        for name in FIELDS - {'paragraphs'}:
            text_field(entry[name], f'{lang}.{name}')
        paragraphs = entry['paragraphs']
        if not isinstance(paragraphs, list) or not 1 <= len(paragraphs) <= 6:
            raise ValueError(f'{lang}.paragraphs must contain 1 to 6 paragraphs.')
        for paragraph in paragraphs:
            text_field(paragraph, f'{lang}.paragraphs')
    return data


def render(data, lang):
    entry = data['languages'][lang]
    company = text_field(data['company'], 'company')
    role = text_field(data['position']['title'], 'position.title')
    if lang == 'it':
        opening = f'Mi candido per la posizione di {role} presso {company}.'
        subject, language, signoff = f'Candidatura - {role}', 'italian', 'Cordiali saluti,'
    else:
        opening = f'I am applying for the {role} position at {company}.'
        subject, language, signoff = f'Application - {role}', 'english', 'Kind regards,'
    paragraphs = [opening, entry['motivation'], *entry['paragraphs'], entry['contribution']]
    replacements = {
        'PERSONAL': (ROOT / 'content/common/personal.tex').read_text(),
        'LANGUAGE': language,
        'PDF_TITLE': tex(subject),
        'COMPANY': tex(company),
        'RECIPIENT': tex(text_field(entry['recipient'], 'recipient')),
        'SUBJECT': tex(subject),
        'SALUTATION': tex(text_field(entry['salutation'], 'salutation')),
        'BODY': '\n\n'.join(tex(text_field(p, 'paragraph')) + r'\par' for p in paragraphs),
        'CLOSING': tex(text_field(entry['closing'], 'closing')),
        'SIGNOFF': signoff,
    }
    template = (ROOT / 'cover-letters/template.tex').read_text()
    # One substitution pass: text from an application is never template code.
    return re.sub(r'@@([A-Z_]+)@@', lambda match: replacements[match[1]], template)


def compile_tex(source, directory):
    latexmk = shutil.which('latexmk')
    if latexmk:
        command = [latexmk, '-lualatex', '-interaction=nonstopmode', '-halt-on-error',
                   f'-outdir={directory}', str(source)]
    else:
        compiler = os.environ.get('CV_TECTONIC_BIN') or shutil.which('tectonic')
        if not compiler:
            compiler = '/Applications/ChatGPT.app/Contents/Resources/tectonic/tectonic'
        if not Path(compiler).is_file() or not os.access(compiler, os.X_OK):
            raise RuntimeError('No compiler found. Use latexmk/LuaLaTeX or CV_TECTONIC_BIN.')
        command = [compiler, '--outdir', str(directory), '--keep-logs', str(source)]
    pdf = directory / source.with_suffix('.pdf').name
    pdf.unlink(missing_ok=True)
    result = subprocess.run(command, cwd=directory, capture_output=True, text=True, timeout=120)
    log = result.stdout + result.stderr
    (directory / f'{source.stem}.build.log').write_text(log)
    if result.returncode or not pdf.is_file():
        raise RuntimeError(f'Compilation failed for {source.name}:\n{log[-3000:]}')
    return pdf


def build(slug, applications=APPLICATIONS, output=OUTPUT, work=WORK):
    slug_name(slug)
    data = load_application(applications / slug / 'application.json')
    # Validate and render both languages before generating anything.
    sources = {lang: render(data, lang) for lang in LANGUAGES}
    directory = work / slug
    directory.mkdir(parents=True, exist_ok=True)
    compiled = []
    for lang, body in sources.items():
        source = directory / f'cover-letter-{lang}.tex'
        source.write_text(body, encoding='utf-8')
        compiled.append(compile_tex(source, directory))
    target = output / slug
    target.mkdir(parents=True, exist_ok=True)
    for pdf in compiled:
        # Keep previous exports until both compilations succeed.
        staging = target / f'.{pdf.name}.new'
        shutil.copyfile(pdf, staging)
        staging.replace(target / pdf.name)
    return [target / pdf.name for pdf in compiled]


def build_all(applications=APPLICATIONS, output=OUTPUT, work=WORK):
    files = []
    if any(applications.glob('*.json')):
        raise ValueError('Legacy flat application files found; move each into company-slug/application.json.')
    for path in sorted(applications.glob('*/application.json')):
        draft = json.loads(path.read_text(encoding='utf-8'))
        if isinstance(draft, dict) and draft.get('ready') is False:
            print(f'Skipping draft: {path.parent.name}')
            continue
        files.extend(build(path.parent.name, applications, output, work))
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--applications-dir', type=Path, default=APPLICATIONS)
    parser.add_argument('--output-dir', type=Path, default=OUTPUT)
    parser.add_argument('--work-dir', type=Path, default=WORK)
    commands = parser.add_subparsers(dest='command', required=True)
    init = commands.add_parser('init', help='Create an editable IT/EN draft; never overwrite.')
    init.add_argument('slug')
    init.add_argument('--company', required=True)
    compile_command = commands.add_parser('build', help='Build both languages for one company.')
    compile_command.add_argument('slug')
    commands.add_parser('build-all', help='Build every ready application in both languages.')
    args = parser.parse_args()
    applications = args.applications_dir.resolve()
    if args.command == 'init':
        print(initialize(args.slug, args.company, applications))
    else:
        common = (applications, args.output_dir.resolve(), args.work_dir.resolve())
        files = build(args.slug, *common) if args.command == 'build' else build_all(*common)
        for path in files:
            print(path)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(f'Cover letter failed: {error}', file=sys.stderr)
        sys.exit(1)
