"""Application generation, validation, safe text rendering and build orchestration."""
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('cover_letter', REPO / 'scripts/cover-letter.py')
letters = importlib.util.module_from_spec(spec)
spec.loader.exec_module(letters)


class CoverLetterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name).resolve()
        self.apps = root / 'applications'
        self.output = root / 'output'
        self.work = root / 'build'
        self.application = letters.initialize('example', 'R&D_Company', self.apps)
        self.initial_text = self.application.read_text()

    def ready(self):
        data = json.loads(self.initial_text)
        data['ready'] = True
        data['position'] = {
            'title': 'Software Engineer',
            'url': 'https://example.com/jobs/software-engineer',
            'location': 'Zurich',
            'requirements': ['Integrate product and infrastructure'],
            'fit': [{'requirement': 'Integrate product and infrastructure',
                     'evidence': 'Netsons web services and CI/CD',
                     'contribution': 'Connect applications and delivery workflows'}],
        }
        for lang in ('it', 'en'):
            data['languages'][lang]['motivation'] = 'A specific reason to join this team.'
            data['languages'][lang]['contribution'] = 'I can connect applications and delivery workflows.'
        self.application.write_text(json.dumps(data))
        return data

    def test_initialize_preserves_existing_application(self):
        original = self.application.read_bytes()
        with self.assertRaises(FileExistsError):
            letters.initialize('example', 'Different company', self.apps)
        self.assertEqual(original, self.application.read_bytes())

    def test_initial_draft_has_both_languages_and_cannot_be_published(self):
        data = json.loads(self.application.read_text())
        self.assertEqual({'it', 'en'}, set(data['languages']))
        self.assertFalse(data['ready'])
        with self.assertRaisesRegex(ValueError, 'ready'):
            letters.load_application(self.application)

    def test_application_has_its_own_company_directory(self):
        self.assertEqual(self.apps / 'example/application.json', self.application)
        self.assertFalse((self.apps / 'example.json').exists())

    def test_position_and_evidence_mapping_required(self):
        for key, value in [('title', ''), ('url', 'not-a-url'),
                           ('requirements', []), ('fit', []), ('fit', [{}])]:
            data = self.ready()
            data['position'][key] = value
            self.application.write_text(json.dumps(data))
            with self.subTest(key=key), self.assertRaises(ValueError):
                letters.load_application(self.application)

    def test_role_title_and_contribution_are_used_in_letter(self):
        data = self.ready()
        rendered = letters.render(data, 'en')
        self.assertIn('Application - Software Engineer', rendered)
        self.assertIn('I can connect applications and delivery workflows.', rendered)

    def test_build_all_reports_legacy_flat_files(self):
        self.apps.mkdir(exist_ok=True)
        (self.apps / 'old.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'Legacy'):
            letters.build_all(self.apps, self.output, self.work)

    def test_slug_cannot_escape_applications_directory(self):
        for slug in ('../elsewhere', '/tmp/out', 'a/b', '', 'UPPER', 'a;rm'):
            with self.subTest(slug=slug), self.assertRaises(ValueError):
                letters.initialize(slug, 'Company', self.apps)

    def test_missing_language_or_motivation_rejected(self):
        for missing in ('en', 'motivation'):
            data = self.ready()
            if missing == 'en':
                del data['languages']['en']
            else:
                data['languages']['it']['motivation'] = ''
            self.application.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                letters.load_application(self.application)

    def test_invalid_field_types_and_unknown_fields_rejected(self):
        for key, value in [('company', []), ('ready', 'yes'), ('unknown', True)]:
            data = self.ready()
            data[key] = value
            self.application.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                letters.load_application(self.application)

    def test_tex_commands_are_rendered_as_literal_text(self):
        data = self.ready()
        data['languages']['it']['motivation'] = r'50% R&D_#1 {test} \\input{private} $ ^ ~'
        rendered = letters.render(data, 'it')
        self.assertIn(r'R\&D\_Company', rendered)
        self.assertIn(r'50\%', rendered)
        self.assertIn(r'\textbackslash{}', rendered)
        self.assertNotIn(r'\\input{private}', rendered)
        self.assertIn("Marco D'Antonio", rendered)
        self.assertNotIn('@@', rendered)

    def test_both_languages_built_before_output_is_updated(self):
        self.ready()
        self.output.mkdir()
        old = self.output / 'example'
        old.mkdir()
        (old / 'cover-letter-it.pdf').write_bytes(b'old pdf')
        calls = []
        def compile_ok(source, directory):
            calls.append(source.name)
            pdf = directory / source.with_suffix('.pdf').name
            pdf.write_bytes(b'new pdf')
            return pdf
        with patch.object(letters, 'compile_tex', side_effect=compile_ok):
            files = letters.build('example', self.apps, self.output, self.work)
        self.assertEqual(2, len(calls))
        self.assertEqual(2, len(files))
        self.assertEqual(b'new pdf', (old / 'cover-letter-it.pdf').read_bytes())
        self.assertTrue((self.work / 'example/cover-letter-en.tex').exists())

    def test_failed_compile_preserves_previous_pdfs(self):
        self.ready()
        target = self.output / 'example'
        target.mkdir(parents=True)
        for lang in ('it', 'en'):
            (target / f'cover-letter-{lang}.pdf').write_bytes(b'previous')
        calls = []
        def fail_second(source, directory):
            calls.append(source.name)
            if len(calls) == 2:
                raise RuntimeError('Compiler error')
            pdf = directory / source.with_suffix('.pdf').name
            pdf.write_bytes(b'new')
            return pdf
        with patch.object(letters, 'compile_tex', side_effect=fail_second):
            with self.assertRaises(RuntimeError):
                letters.build('example', self.apps, self.output, self.work)
        for lang in ('it', 'en'):
            self.assertEqual(b'previous', (target / f'cover-letter-{lang}.pdf').read_bytes())

    def test_build_all_skips_drafts_and_builds_ready_applications(self):
        self.ready()
        letters.initialize('draft', 'Draft Company', self.apps)
        with patch.object(letters, 'build', return_value=[]) as build:
            letters.build_all(self.apps, self.output, self.work)
        self.assertEqual(1, build.call_count)
        self.assertEqual('example', build.call_args.args[0])

    def test_invalid_paragraphs_and_control_characters_rejected(self):
        for value in ([], 'not a list', [''], ['bad\x00text'], ['x' * 6001]):
            data = self.ready()
            data['languages']['it']['paragraphs'] = value
            self.application.write_text(json.dumps(data))
            with self.subTest(value=str(value)[:30]), self.assertRaises(ValueError):
                letters.load_application(self.application)

    def test_compile_uses_latexmk_and_writes_log(self):
        self.work.mkdir()
        source = self.work / 'letter.tex'
        source.write_text('source')
        def run(command, **kwargs):
            self.assertIn('-lualatex', command)
            source.with_suffix('.pdf').write_bytes(b'pdf')
            return SimpleNamespace(returncode=0, stdout='compiled', stderr='')
        with patch.object(letters.shutil, 'which', return_value='/bin/latexmk'), \
             patch.object(letters.subprocess, 'run', side_effect=run):
            self.assertEqual(source.with_suffix('.pdf'), letters.compile_tex(source, self.work))
        self.assertEqual('compiled', (self.work / 'letter.build.log').read_text())

    def test_compile_does_not_accept_a_stale_pdf(self):
        self.work.mkdir()
        source = self.work / 'letter.tex'
        source.write_text('source')
        source.with_suffix('.pdf').write_bytes(b'stale')
        with patch.object(letters.shutil, 'which', return_value='/bin/latexmk'), \
             patch.object(letters.subprocess, 'run', return_value=SimpleNamespace(
                 returncode=0, stdout='no new pdf', stderr='')):
            with self.assertRaisesRegex(RuntimeError, 'Compilation failed'):
                letters.compile_tex(source, self.work)

    def test_tectonic_fallback_and_missing_compiler(self):
        self.work.mkdir()
        source = self.work / 'letter.tex'
        source.write_text('source')
        compiler = self.work / 'tectonic'
        compiler.write_text('fake executable')
        compiler.chmod(0o755)
        def run(command, **kwargs):
            self.assertEqual(str(compiler), command[0])
            source.with_suffix('.pdf').write_bytes(b'pdf')
            return SimpleNamespace(returncode=0, stdout='', stderr='')
        with patch.object(letters.shutil, 'which', return_value=None), \
             patch.dict(letters.os.environ, {'CV_TECTONIC_BIN': str(compiler)}), \
             patch.object(letters.subprocess, 'run', side_effect=run):
            letters.compile_tex(source, self.work)
        with patch.object(letters.shutil, 'which', return_value=None), \
             patch.dict(letters.os.environ, {'CV_TECTONIC_BIN': '/missing/compiler'}):
            with self.assertRaisesRegex(RuntimeError, 'No compiler'):
                letters.compile_tex(source, self.work)

    def test_cli_init_build_and_build_all(self):
        common = ['cover-letter.py', '--applications-dir', str(self.apps),
                  '--output-dir', str(self.output), '--work-dir', str(self.work)]
        with patch.object(letters.sys, 'argv', common + ['init', 'cli', '--company', 'Company']):
            letters.main()
        self.assertTrue((self.apps / 'cli/application.json').exists())
        with patch.object(letters, 'build', return_value=[self.output / 'letter.pdf']) as build, \
             patch.object(letters.sys, 'argv', common + ['build', 'cli']):
            letters.main()
        build.assert_called_once_with('cli', self.apps, self.output, self.work)
        with patch.object(letters, 'build_all', return_value=[]) as build_all, \
             patch.object(letters.sys, 'argv', common + ['build-all']):
            letters.main()
        build_all.assert_called_once_with(self.apps, self.output, self.work)
