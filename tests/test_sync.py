import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.upstream = self.root / 'upstream'
        self.upstream.mkdir()
        self.repo = self.root / 'fork'
        self.plugin = self.repo / 'plugins/pstack-for-codex'
        self.plugin.mkdir(parents=True)
        self.git('init', '-q')
        self.git('config', 'user.email', 'fixture@example.com')
        self.git('config', 'user.name', 'Fixture')
        self.file('skills/example/reference.md', 'first\nsecond\nthird\n')
        self.file('.cursor-plugin/plugin.json', json.dumps({'version': '0.15.23'}))
        self.old = self.commit()
        (self.plugin / 'skills/example').mkdir(parents=True)
        (self.plugin / 'skills/example/reference.md').write_text('Codex first\nsecond\nthird\n')
        (self.plugin / 'plugin.json').write_text(json.dumps({'name':'pstack-for-codex','version':'0.15.23'}))
        (self.repo / 'upstream.json').write_text(json.dumps({'commit':self.old}))

    def git(self, *args):
        return subprocess.check_output(['git','-C',str(self.upstream),*args], text=True).strip()

    def file(self, name, text):
        p = self.upstream / 'pstack' / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def commit(self):
        self.git('add', '.')
        self.git('commit', '-qm', 'fixture')
        return self.git('rev-parse', 'HEAD')

    def run_sync(self, sha):
        from sync_upstream import sync
        # These unit fixtures model merge behavior, not the complete plugin schema.
        # The real CLI uses package validation; staging is exercised separately.
        return sync(self.repo, self.upstream, sha, validator=None)

    def repo_files(self):
        return {str(p.relative_to(self.repo)): p.read_bytes()
                for p in self.repo.rglob('*') if p.is_file()}

    def test_version_only_upstream_change_updates_version_and_checkpoint(self):
        self.file('.cursor-plugin/plugin.json', json.dumps({'version': '0.16.0'}))
        head = self.commit()
        content = (self.plugin / 'skills/example/reference.md').read_bytes()
        self.assertTrue(self.run_sync(head))
        self.assertEqual(json.loads((self.plugin / 'plugin.json').read_text())['version'], '0.16.0')
        self.assertEqual(json.loads((self.repo / 'upstream.json').read_text())['commit'], head)
        self.assertEqual((self.plugin / 'skills/example/reference.md').read_bytes(), content)
        saved = self.repo_files()
        self.assertFalse(self.run_sync(head))
        self.assertEqual(self.repo_files(), saved)

    def test_legacy_fork_version_is_aligned_even_at_the_same_checkpoint(self):
        path = self.plugin / 'plugin.json'
        manifest = json.loads(path.read_text())
        manifest['version'] = '1.0.5'
        path.write_text(json.dumps(manifest))
        self.assertTrue(self.run_sync(self.old))
        self.assertEqual(json.loads(path.read_text())['version'], '0.15.23')
        self.assertFalse(self.run_sync(self.old))

    def test_invalid_or_missing_upstream_version_blocks_without_writes(self):
        from sync_upstream import SyncConflict
        for data in ['{}', '[]', '{"version": "../../bad"}', '{"version": 23}', 'not json']:
            with self.subTest(data=data):
                self.file('.cursor-plugin/plugin.json', data)
                head = self.commit()
                before = self.repo_files()
                with self.assertRaisesRegex(SyncConflict, 'upstream pstack version'):
                    self.run_sync(head)
                self.assertEqual(self.repo_files(), before)
        (self.upstream / 'pstack/.cursor-plugin/plugin.json').unlink()
        head = self.commit()
        before = self.repo_files()
        with self.assertRaisesRegex(SyncConflict, 'upstream pstack version'):
            self.run_sync(head)
        self.assertEqual(self.repo_files(), before)

    def arena_fixture(self, name):
        return (Path(__file__).parent / 'fixtures/arena' / (name + '.md')).read_text()

    def prepare_arena(self):
        self.file('skills/arena/SKILL.md', self.arena_fixture('upstream-before'))
        self.old = self.commit()
        (self.repo / 'upstream.json').write_text(json.dumps({'commit': self.old}))
        path = self.plugin / 'skills/arena/SKILL.md'
        path.parent.mkdir(parents=True)
        path.write_text(self.arena_fixture('codex-before'))
        protected = {
            'skills/thermo-nuclear-code-quality-review/SKILL.md': 'independent review\n',
            'skills/thermo-nuclear-code-quality-review/agents/openai.yaml': 'independent metadata\n',
            'LICENSE-cursor-team-kit': 'independent attribution\n',
        }
        for name, content in protected.items():
            target = self.plugin / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
        self.file('skills/arena/SKILL.md', self.arena_fixture('upstream-after'))
        self.file('skills/thermo-nuclear-code-quality-review/SKILL.md', 'upstream collision\n')
        self.file('skills/thermo-nuclear-code-quality-review/agents/openai.yaml', 'upstream metadata\n')
        return self.commit(), path, protected

    def test_october_11_arena_distillation_preserves_port_and_independent_review(self):
        new, path, protected = self.prepare_arena()
        from sync_upstream import SyncConflict
        try:
            self.assertTrue(self.run_sync(new))
        except SyncConflict as error:
            self.fail(f'Known routine upstream update must synchronize: {error}')
        result = path.read_text()
        self.assertIn('naming the alternatives it considered and what it rejected', result)
        self.assertIn('Read Candidate count from explicitly loaded .agents/pstack-config.md', result)
        self.assertIn('native nonblocking delegation when supported', result)
        self.assertIn('Do not claim cross-model independence', result)
        self.assertNotIn('## Start', result)
        self.assertNotIn('~/.cursor/', result)
        self.assertNotIn('run_in_background:', result)
        self.assertNotIn('claude-opus-', result)
        for name, content in protected.items():
            self.assertEqual((self.plugin / name).read_text(), content)
        self.assertEqual(json.loads((self.repo / 'upstream.json').read_text())['commit'], new)
        self.assertFalse(self.run_sync(new))

    def test_next_arena_wording_update_does_not_repeat_port_conflict(self):
        new, path, protected = self.prepare_arena()
        self.run_sync(new)
        # A genuine local addition remains a separate side of the three-way merge.
        path.write_text(path.read_text() + '\nLocal completion receipt.\n')
        incoming = self.arena_fixture('upstream-after').replace(
            '1. State the artifact each candidate is producing.',
            '1. State the concrete artifact each candidate is producing.')
        self.file('skills/arena/SKILL.md', incoming)
        self.assertTrue(self.run_sync(self.commit()))
        self.assertIn('State the concrete artifact', path.read_text())
        self.assertIn('Local completion receipt.', path.read_text())
        self.assertIn('Do not claim cross-model independence', path.read_text())
        for name, content in protected.items():
            self.assertEqual((self.plugin / name).read_text(), content)

    def test_unrecognized_arena_model_change_blocks_without_advancing_checkpoint(self):
        new, path, protected = self.prepare_arena()
        self.run_sync(new)
        incoming = self.arena_fixture('upstream-after').replace(
            'If the Task tool rejects a configured entry, run that seat on its family\'s default and say so.',
            'If the Task tool rejects a configured entry, stop every candidate immediately.')
        self.file('skills/arena/SKILL.md', incoming)
        # A second compatible change must also stay unapplied when one file is ambiguous.
        self.file('skills/example/reference.md', 'first\nsecond\nupstream third\n')
        before = self.repo_files()
        from sync_upstream import SyncConflict
        with self.assertRaises(SyncConflict):
            self.run_sync(self.commit())
        self.assertEqual(self.repo_files(), before)

    def test_skill_frontmatter_is_normalized_before_merge(self):
        from sync_upstream import normalize_skill
        name = 'skills/example/SKILL.md'
        old = '---\nname: Example\ndescription: First description.\ndisable-model-invocation: true\n---\n\n# Example\n\nBody.\n'
        self.file(name, old)
        base = self.commit()
        (self.repo / 'upstream.json').write_text(json.dumps({'commit': base}))
        (self.plugin / name).write_bytes(normalize_skill(old.encode(), name))
        new = old.replace('First description.', 'Updated description.')
        self.file(name, new)
        self.assertTrue(self.run_sync(self.commit()))
        self.assertEqual((self.plugin / name).read_bytes(), normalize_skill(new.encode(), name))

    def test_normalized_skill_deletion_is_not_misclassified_as_manual_edit(self):
        from sync_upstream import normalize_skill
        name = 'skills/example/SKILL.md'
        old = '---\nname: Example\ndescription: Explain a thing.\n---\n\n# Example\n'
        self.file(name, old)
        base = self.commit()
        (self.repo / 'upstream.json').write_text(json.dumps({'commit': base}))
        (self.plugin / name).write_bytes(normalize_skill(old.encode(), name))
        (self.upstream / 'pstack' / name).unlink()
        self.assertTrue(self.run_sync(self.commit()))
        self.assertFalse((self.plugin / name).exists())

    def test_manual_arena_edit_remains_a_real_merge_conflict(self):
        new, path, _ = self.prepare_arena()
        path.write_text(path.read_text().replace(
            'native nonblocking delegation when supported', 'serial delegation only'))
        before = self.repo_files()
        from sync_upstream import SyncConflict
        with self.assertRaises(SyncConflict):
            self.run_sync(new)
        self.assertEqual(self.repo_files(), before)

    def test_duplicate_translation_input_is_rejected_atomically(self):
        new, _, _ = self.prepare_arena()
        self.run_sync(new)
        incoming = self.arena_fixture('upstream-after')
        runner = next(line for line in incoming.splitlines(True)
                      if line.startswith('3. Pick the runners.'))
        self.file('skills/arena/SKILL.md', incoming + '\n' + runner)
        before = self.repo_files()
        from sync_upstream import SyncConflict
        with self.assertRaises(SyncConflict):
            self.run_sync(self.commit())
        self.assertEqual(self.repo_files(), before)

    def test_package_validation_failure_leaves_source_and_checkpoint_unchanged(self):
        self.file('skills/example/reference.md', 'first\nsecond\nupstream third\n')
        new = self.commit()
        before = self.repo_files()
        def reject(staged):
            self.assertNotEqual(staged.resolve(), self.repo.resolve())
            self.assertEqual((staged / 'plugins/pstack-for-codex/skills/example/reference.md').read_text(),
                             'Codex first\nsecond\nupstream third\n')
            self.assertEqual(json.loads((staged / 'upstream.json').read_text())['commit'], new)
            self.assertEqual(self.repo_files(), before)
            raise ValueError('unsupported runtime instructions')
        from sync_upstream import SyncConflict, sync
        with self.assertRaisesRegex(SyncConflict, 'validation'):
            sync(self.repo, self.upstream, new, validator=reject)
        self.assertEqual(self.repo_files(), before)

    def test_successful_package_validation_precedes_checkpoint_write(self):
        self.file('skills/example/reference.md', 'first\nsecond\nupstream third\n')
        new = self.commit()
        before = self.repo_files()
        validated = []
        def accept(staged):
            self.assertEqual(self.repo_files(), before)
            self.assertEqual(json.loads((staged / 'upstream.json').read_text())['commit'], new)
            self.assertEqual(json.loads((staged / 'plugins/pstack-for-codex/plugin.json').read_text())['version'], '0.15.23')
            validated.append(staged)
        from sync_upstream import sync
        self.assertTrue(sync(self.repo, self.upstream, new, validator=accept))
        self.assertEqual(len(validated), 1)
        self.assertEqual(json.loads((self.repo / 'upstream.json').read_text())['commit'], new)

    def test_default_package_validation_cannot_be_bypassed_by_sync(self):
        # The intentionally incomplete unit package must fail the real validator.
        self.file('skills/example/reference.md', 'first\nsecond\nupstream third\n')
        before = self.repo_files()
        from sync_upstream import SyncConflict, sync
        with self.assertRaisesRegex(SyncConflict, 'validation'):
            sync(self.repo, self.upstream, self.commit())
        self.assertEqual(self.repo_files(), before)

    def test_reviewed_instruction_removal_cannot_be_reused_on_a_different_source(self):
        fixtures = Path(__file__).parent / 'fixtures/how'
        name = 'skills/how/SKILL.md'
        self.file(name, (fixtures / 'upstream-before.md').read_text())
        base = self.commit()
        (self.repo / 'upstream.json').write_text(json.dumps({'commit': base}))
        target = self.plugin / name
        target.parent.mkdir(parents=True)
        target.write_bytes((fixtures / 'codex-before.md').read_bytes())
        incoming = (fixtures / 'upstream-after.md').read_text()
        self.file(name, incoming.replace('Dropping', 'Removing') + '\nUnreviewed additional instruction.\n')
        before = self.repo_files()
        from sync_upstream import SyncConflict
        with self.assertRaisesRegex(SyncConflict, 'translation'):
            self.run_sync(self.commit())
        self.assertEqual(self.repo_files(), before)
        # The exact reviewed source succeeds; its next ordinary wording edit does too.
        self.file(name, incoming)
        self.assertTrue(self.run_sync(self.commit()))
        self.file(name, incoming.replace('When in doubt, take the simple path.',
                                         'When uncertain, take the simple path.'))
        self.assertTrue(self.run_sync(self.commit()))
        self.assertIn('When uncertain', target.read_text())
        self.assertNotIn('subagent_type:', target.read_text())

    def test_staging_does_not_hide_forbidden_files_inside_the_real_package(self):
        project = Path(__file__).resolve().parents[1]
        shutil.copytree(project / 'plugins/pstack-for-codex', self.plugin, dirs_exist_ok=True)
        shutil.copytree(project / 'schemas', self.repo / 'schemas')
        shutil.copytree(project / '.agents', self.repo / '.agents')
        from sync_upstream import SyncConflict, sync
        from validate import validate
        for directory in ['__pycache__', '.git']:
            with self.subTest(directory=directory):
                forbidden = self.plugin / 'skills/arena' / directory
                forbidden.mkdir()
                (forbidden / 'unexpected-file').write_text('must be visible to validation\n')
                self.file('skills/example/reference.md', f'first\nsecond\n{directory} third\n')
                with self.assertRaises(AssertionError):
                    validate(self.repo)
                before = self.repo_files()
                with self.assertRaisesRegex(SyncConflict, 'validation'):
                    sync(self.repo, self.upstream, self.commit())
                self.assertEqual(self.repo_files(), before)
                shutil.rmtree(forbidden)

    def test_nonoverlapping_change_preserves_codex_adaptation(self):
        self.file('skills/example/reference.md', 'first\nsecond\nupstream third\n')
        new = self.commit()
        self.assertTrue(self.run_sync(new))
        self.assertEqual((self.plugin/'skills/example/reference.md').read_text(), 'Codex first\nsecond\nupstream third\n')
        self.assertEqual(json.loads((self.repo/'upstream.json').read_text())['commit'],new)
        self.assertEqual(json.loads((self.plugin/'plugin.json').read_text())['version'],'0.15.23')
        self.assertFalse(self.run_sync(new))

    def test_conflict_does_not_change_files_or_checkpoint(self):
        self.file('skills/example/reference.md','upstream first\nsecond\nthird\n')
        new = self.commit()
        before = {str(p.relative_to(self.repo)):p.read_bytes() for p in self.repo.rglob('*') if p.is_file()}
        from sync_upstream import SyncConflict
        with self.assertRaises(SyncConflict): self.run_sync(new)
        after = {str(p.relative_to(self.repo)):p.read_bytes() for p in self.repo.rglob('*') if p.is_file()}
        self.assertEqual(before,after)

    def test_new_skill_gets_native_metadata_and_runtime_link(self):
        self.file('skills/new-skill/SKILL.md','---\nname: New Skill\ndescription: Explain a new thing.\nmode: true\n---\n\n# New skill\n')
        self.run_sync(self.commit())
        body=(self.plugin/'skills/new-skill/SKILL.md').read_text()
        self.assertIn('name: new-skill',body)
        self.assertNotIn('mode: true',body)
        self.assertIn('../../CODEX-RUNTIME.md',body)
        self.assertTrue((self.plugin/'skills/new-skill/agents/openai.yaml').is_file())

    def test_upstream_deletion_does_not_delete_modified_fork_file(self):
        (self.upstream/'pstack/skills/example/reference.md').unlink()
        from sync_upstream import SyncConflict
        with self.assertRaises(SyncConflict):self.run_sync(self.commit())
        self.assertTrue((self.plugin/'skills/example/reference.md').exists())

    def test_upstream_outside_pstack_has_no_effect(self):
        (self.upstream/'elsewhere.md').write_text('other plugin')
        self.assertFalse(self.run_sync(self.commit()))
        self.assertEqual(json.loads((self.plugin/'plugin.json').read_text())['version'],'0.15.23')

    def test_new_symlink_is_rejected(self):
        (self.upstream/'pstack/skills/escape').symlink_to('/etc/passwd')
        from sync_upstream import SyncConflict
        with self.assertRaises(SyncConflict):self.run_sync(self.commit())

    def test_independent_review_survives_pstack_add_edit_and_delete(self):
        name = 'skills/thermo-nuclear-code-quality-review'
        protected = {
            name + '/SKILL.md': 'independent Codex review\n',
            name + '/agents/openai.yaml': 'independent invocation metadata\n',
            'LICENSE-cursor-team-kit': 'Cursor MIT attribution\n',
        }
        for path, text in protected.items():
            target = self.plugin / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)
        for action in ['add', 'edit', 'delete']:
            with self.subTest(action=action):
                if action == 'delete':
                    (self.upstream / 'pstack' / name / 'SKILL.md').unlink()
                    (self.upstream / 'pstack' / name / 'agents/openai.yaml').unlink()
                else:
                    self.file(name + '/SKILL.md', f'pstack {action}\n')
                    self.file(name + '/agents/openai.yaml', f'pstack metadata {action}\n')
                # A real update elsewhere ensures the full synchronization runs.
                self.file('skills/example/reference.md', f'first\nsecond\n{action}\n')
                self.assertTrue(self.run_sync(self.commit()))
                for path, text in protected.items():
                    self.assertEqual((self.plugin / path).read_text(), text)

    def test_only_same_name_upstream_skill_does_not_trigger_sync(self):
        self.file('skills/thermo-nuclear-code-quality-review/SKILL.md', 'upstream collision\n')
        self.assertFalse(self.run_sync(self.commit()))
        self.assertEqual(json.loads((self.repo / 'upstream.json').read_text())['commit'], self.old)

if __name__ == '__main__':unittest.main()
