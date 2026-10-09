import json
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
        self.old = self.commit()
        (self.plugin / 'skills/example').mkdir(parents=True)
        (self.plugin / 'skills/example/reference.md').write_text('Codex first\nsecond\nthird\n')
        (self.plugin / 'plugin.json').write_text(json.dumps({'name':'pstack-for-codex','version':'1.0.0'}))
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
        return sync(self.repo, self.upstream, sha)

    def test_nonoverlapping_change_preserves_codex_adaptation(self):
        self.file('skills/example/reference.md', 'first\nsecond\nupstream third\n')
        new = self.commit()
        self.assertTrue(self.run_sync(new))
        self.assertEqual((self.plugin/'skills/example/reference.md').read_text(), 'Codex first\nsecond\nupstream third\n')
        self.assertEqual(json.loads((self.repo/'upstream.json').read_text())['commit'],new)
        self.assertEqual(json.loads((self.plugin/'plugin.json').read_text())['version'],'1.0.1')
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
        self.assertEqual(json.loads((self.plugin/'plugin.json').read_text())['version'],'1.0.0')

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
