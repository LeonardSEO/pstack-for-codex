"""Replay every managed change from the failed October 14 scheduled sync."""
import json
import unittest
from pathlib import Path

import test_oct12_sync as fixtures
from sync_upstream import SyncConflict, adapt, sync, target_path
from validate import validate


class October14SyncTests(unittest.TestCase):
    fixture = Path(__file__).parent / 'fixtures/oct14'
    fork_version = '0.15.23'
    setUp = fixtures.October12SyncTests.setUp
    git = fixtures.October12SyncTests.git
    commit = fixtures.October12SyncTests.commit
    copy_fixture = fixtures.October12SyncTests.copy_fixture
    install_upstream = fixtures.October12SyncTests.install_upstream
    files = fixtures.October12SyncTests.files

    def test_complete_pending_interval_validates_and_repeats_unchanged(self):
        before = self.files()
        checked = []

        def check(candidate):
            self.assertEqual(self.files(), before)
            self.assertEqual(validate(candidate), self.expected_skill_count)
            checked.append(True)

        self.assertTrue(sync(self.root, self.upstream, self.new, validator=check))
        self.assertEqual(checked, [True])
        self.assertEqual(json.loads((self.plugin / 'plugin.json').read_text())['version'], '0.15.24')
        self.assertEqual(json.loads((self.root / 'upstream.json').read_text())['commit'], self.new)
        for name, versions in self.manifest['files'].items():
            source = (self.fixture / 'upstream-after' / name).read_bytes()
            expected, _ = adapt(source, name, self.adaptations)
            actual = self.plugin / target_path(name)
            original = (self.fixture / 'codex-before' / target_path(name)).read_bytes() if 'codex-before' in versions else None
            base, _ = adapt((self.fixture / 'upstream-before' / name).read_bytes(), name, self.adaptations) if 'upstream-before' in versions else (None, set())
            if original == base or self.adaptations.get(name, {}).get('legacy_renderings'):
                self.assertEqual(actual.read_bytes(), expected, name)
            self.assertEqual(actual.stat().st_mode & 0o777, versions['upstream-after']['mode'], name)
        audit = (self.plugin / 'skills/poteto-mode/scripts/worktree-audit.sh').read_text()
        self.assertIn('PSTACK_TRANSCRIPTS_DIR', audit)
        self.assertNotIn('~/.cursor/', audit)
        self.assertIn('150 words', (self.plugin / 'skills/ketchup/SKILL.md').read_text())
        shipping = (self.plugin / 'skills/poteto-mode/playbooks/shipping.md').read_text()
        self.assertIn('<installed-poteto-mode-directory>/scripts/watch-pr/watch-pr --queued-stack', shipping)
        after = self.files()
        for name, value in before.items():
            if 'thermo-nuclear-code-quality-review/' in name or name.endswith('LICENSE-cursor-team-kit'):
                self.assertEqual(after[name], value)
        self.assertFalse(sync(self.root, self.upstream, self.new))
        self.assertEqual(self.files(), after)

    def test_future_append_to_translated_paragraph_keeps_upstream_guidance(self):
        self.assertTrue(sync(self.root, self.upstream, self.new))
        path = self.upstream / 'pstack/skills/arena/SKILL.md'
        source = path.read_text()
        sentence = ' Report the reason for each candidate selection.'
        lines = source.splitlines(keepends=True)
        index = next(i for i, line in enumerate(lines) if line.startswith('3. Pick the runners.'))
        lines[index] = lines[index].rstrip('\n') + sentence + '\n'
        path.write_text(''.join(lines))
        self.assertTrue(sync(self.root, self.upstream, self.commit()))
        actual = (self.plugin / 'skills/arena/SKILL.md').read_text()
        self.assertIn(sentence, actual)
        self.assertNotIn('~/.cursor/', actual)

    def test_local_conflicting_edit_is_not_discarded(self):
        path = self.plugin / 'skills/ketchup/SKILL.md'
        source = path.read_text()
        self.assertIn('250 words', source)
        path.write_text(source.replace('250 words', '500 words'))
        before = self.files()
        with self.assertRaisesRegex(SyncConflict, 'Conflicting upstream and Codex edits'):
            sync(self.root, self.upstream, self.new)
        self.assertEqual(self.files(), before)

    def test_rewritten_translation_is_taken_over_when_codex_compatible(self):
        self.assertTrue(sync(self.root, self.upstream, self.new))
        path = self.upstream / 'pstack/skills/arena/SKILL.md'
        source = path.read_text()
        line = next(line for line in source.splitlines() if line.startswith('3. Pick the runners.'))
        replacement = '3. Pick runners using the host defaults and explain their roles.'
        path.write_text(source.replace(line, replacement))
        self.assertTrue(sync(self.root, self.upstream, self.commit()))
        self.assertIn(replacement, (self.plugin / 'skills/arena/SKILL.md').read_text())

    def test_rewritten_translation_with_unsupported_syntax_blocks_without_writes(self):
        self.assertTrue(sync(self.root, self.upstream, self.new))
        path = self.upstream / 'pstack/skills/arena/SKILL.md'
        source = path.read_text()
        line = next(line for line in source.splitlines() if line.startswith('3. Pick the runners.'))
        path.write_text(source.replace(line, '3. Pick runners from ~/.cursor/new-settings.json.'))
        before = self.files()
        with self.assertRaisesRegex(SyncConflict, 'validation'):
            sync(self.root, self.upstream, self.commit())
        self.assertEqual(self.files(), before)


if __name__ == '__main__':
    unittest.main()
