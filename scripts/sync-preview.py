#!/usr/bin/env python3
"""Round-trip modular TeX sources and the editable standalone desktop preview.

Source markers preserve file ownership. Per-file hashes reject concurrent edits;
missing markers or state are errors, never permission to overwrite a preview.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
INPUT = re.compile(r'\\input\{([^}]+)\}')
MARKER = re.compile(r'% CV-(BEGIN|END): ([^\n|]+?)(?: \| ([^\n]+))?\n')


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def source_path(name):
    path = (ROOT / name).resolve()
    if not path.is_relative_to(ROOT) or path.suffix != '.tex':
        raise ValueError(f'Invalid source path: {name}')
    return path


def render(lang, theme):
    hashes = {}
    active = set()

    def expand(name, original):
        if name in active:
            raise ValueError(f'Cyclic input: {name}')
        active.add(name)
        text = source_path(name).read_text()
        hashes[name] = digest(text)

        def include(match):
            expr = match.group(1)
            actual = expr.replace(r'\CVLanguage', lang).replace(r'\CVTheme', theme)
            return expand(actual, expr)

        body = INPUT.sub(include, text)
        active.remove(name)
        # A commented terminator avoids introducing blank paragraphs inside macros.
        return f'% CV-BEGIN: {name} | {original}\n{body}%\n% CV-END: {name}\n'

    prefix = f'\\def\\CVLanguage{{{lang}}}\\def\\CVTheme{{{theme}}}\n'
    return prefix + expand('main.tex', 'main.tex'), hashes


def unpack(text, lang, theme):
    prefix = f'\\def\\CVLanguage{{{lang}}}\\def\\CVTheme{{{theme}}}\n'
    if not text.startswith(prefix):
        raise ValueError('Preview language/theme wrapper changed; restore it before syncing.')
    text = text[len(prefix):]
    stack, sources, cursor = [], {}, 0
    for match in MARKER.finditer(text):
        chunk = text[cursor:match.start()]
        if stack:
            stack[-1]['parts'].append(chunk)
        elif chunk.strip():
            raise ValueError('Text outside source markers; place edits inside their source block.')
        kind, name, original = match.groups()
        source_path(name)
        if kind == 'BEGIN':
            if not original:
                raise ValueError(f'Missing input expression: {name}')
            stack.append({'name': name, 'original': original, 'parts': []})
        else:
            if not stack or stack[-1]['name'] != name:
                raise ValueError(f'Unbalanced source marker: {name}')
            node = stack.pop()
            body = ''.join(node['parts'])
            if not body.endswith('%\n'):
                raise ValueError(f'Missing closing-marker newline: {name}')
            body = body[:-2]
            if name in sources and sources[name] != body:
                raise ValueError(f'Conflicting repeated source: {name}')
            sources[name] = body
            if stack:
                stack[-1]['parts'].append(r'\input{' + node['original'] + '}')
        cursor = match.end()
    if stack or text[cursor:].strip() or 'main.tex' not in sources:
        raise ValueError('Missing/incomplete source markers; preview was preserved.')
    return sources


def sync(lang, theme, initialize=False):
    directory = ROOT / 'build' / f'review-{theme}'
    preview = directory / f'cv-{lang}.tex'
    state_file = directory / f'.sync-{lang}.json'
    directory.mkdir(parents=True, exist_ok=True)
    if preview.exists() and not initialize:
        if not state_file.exists():
            raise ValueError(f'Missing sync state for {preview}; preserve/reconcile it explicitly.')
        state = json.loads(state_file.read_text())
        text = preview.read_text()
        if digest(text) != state['preview']:
            sources = unpack(text, lang, theme)
            if set(sources) != set(state['sources']):
                raise ValueError('Source blocks added/removed; reconcile modular inputs first.')
            updates = {}
            for name, edited in sources.items():
                baseline = state['sources'][name]
                current = source_path(name).read_text()
                if digest(edited) != baseline:
                    if digest(current) != baseline and current != edited:
                        raise ValueError(f'Concurrent edits in {name}; no files were overwritten.')
                    updates[name] = edited
            # Validate every conflict before writing any file.
            for name, edited in updates.items():
                source_path(name).write_text(edited)
    elif preview.exists() and initialize:
        backup = preview.with_suffix('.pre-sync.tex')
        if not backup.exists():
            backup.write_text(preview.read_text())
    text, hashes = render(lang, theme)
    # Avoid unnecessary editor reloads when nothing changed.
    if not preview.exists() or preview.read_text() != text:
        preview.write_text(text)
    state_file.write_text(json.dumps({'preview': digest(text), 'sources': hashes}, indent=2) + '\n')
    return preview


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('language', choices=('it', 'en'))
    parser.add_argument('--theme', default='single-column', choices=('single-column', 'double-column'))
    parser.add_argument('--initialize', action='store_true', help='Initial reconciliation only; backs up existing preview.')
    args = parser.parse_args()
    print(sync(args.language, args.theme, args.initialize))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError) as error:
        print(f'Preview sync failed: {error}', file=sys.stderr)
        sys.exit(1)
