"""Replay the complete upstream interval that blocked workflow run #5."""
import json
import unittest
from pathlib import Path

import test_oct12_sync as fixtures
from sync_upstream import SyncConflict, adapt, sync
from validate import validate


class LatestSyncTests(unittest.TestCase):
    fixture = Path(__file__).parent / 'fixtures/oct13-latest'
    fork_version = '1.0.4'
    setUp = fixtures.October12SyncTests.setUp
    git = fixtures.October12SyncTests.git
    commit = fixtures.October12SyncTests.commit
    copy_fixture = fixtures.October12SyncTests.copy_fixture
    install_upstream = fixtures.October12SyncTests.install_upstream
    files = fixtures.October12SyncTests.files

    def test_latest_upstream_validates_and_repeats_unchanged(self):
        help_path = self.plugin / 'skills/poteto-help/SKILL.md'
        before = self.files()
        calls = []

        def check(staged):
            self.assertEqual(self.files(), before)
            self.assertEqual(validate(staged), self.expected_skill_count)
            calls.append(True)

        self.assertTrue(sync(self.root, self.upstream, self.new, validator=check))
        self.assertEqual(calls, [True])
        help_text = help_path.read_text()
        self.assertIn('../in-your-own-words/SKILL.md', help_text)
        self.assertIn('in a short reply with visuals', help_text)
        self.assertIn('Native skill metadata disables implicit invocation.', help_text)
        role = (self.plugin / 'agents/poteto-agent.md').read_text()
        self.assertIn('Use the absolute path your parent gave you.', role)
        self.assertIn('relative to this bundled role file', role)
        self.assertNotIn('~/.cursor/', role)
        self.assertIn('250 words', (self.plugin / 'skills/ketchup/SKILL.md').read_text())
        self.assertIn('always-on signal', (self.plugin / 'skills/principle-fix-root-causes/SKILL.md').read_text())
        self.assertTrue((self.plugin / 'skills/in-your-own-words/agents/openai.yaml').is_file())
        self.assertEqual(json.loads((self.root / 'upstream.json').read_text())['commit'], self.new)
        self.assertEqual(json.loads((self.plugin / 'plugin.json').read_text())['version'], '0.15.23')
        after = self.files()
        for name, value in before.items():
            if 'thermo-nuclear-code-quality-review/' in name or name.endswith('LICENSE-cursor-team-kit'):
                self.assertEqual(after[name], value)
        self.assertFalse(sync(self.root, self.upstream, self.new))
        self.assertEqual(self.files(), after)

    def test_future_help_table_edits_flow_without_another_registry_update(self):
        self.assertTrue(sync(self.root, self.upstream, self.new))
        local = self.plugin / 'skills/poteto-help/SKILL.md'
        local.write_text(local.read_text() + '\nLocal note: report the project name.\n')
        path = self.upstream / 'pstack/skills/poteto-help/SKILL.md'
        text = path.read_text().replace('in a short reply with visuals', 'with verified results and relevant visuals')
        text = text.replace('## Pick a skill', '## Pick a skill\n\nReport the source of each recommendation.')
        path.write_text(text)
        self.assertTrue(sync(self.root, self.upstream, self.commit()))
        actual = (self.plugin / 'skills/poteto-help/SKILL.md').read_text()
        self.assertIn('with verified results and relevant visuals', actual)
        self.assertIn('Report the source of each recommendation.', actual)
        self.assertIn('The host controls model availability', actual)
        self.assertIn('Local note: report the project name.', actual)

    def test_local_edit_colliding_with_legacy_migration_is_not_discarded(self):
        path = self.plugin / 'skills/poteto-help/SKILL.md'
        path.write_text(path.read_text() + '\nLocal note: report the project name.\n')
        before = self.files()
        with self.assertRaisesRegex(SyncConflict, 'Conflicting upstream and Codex edits'):
            sync(self.root, self.upstream, self.new)
        self.assertEqual(self.files(), before)

    def test_rewritten_installation_instructions_are_taken_from_upstream(self):
        name = 'skills/poteto-help/SKILL.md'
        path = self.upstream / 'pstack' / name
        replacement = '1. Install using your host plugin marketplace.'
        path.write_text(path.read_text().replace('1. Install with `/add-plugin pstack` in chat, or from Customize in the sidebar.',
                                                replacement))
        self.assertTrue(sync(self.root, self.upstream, self.commit()))
        self.assertIn(replacement, (self.plugin / name).read_text())

    def test_untranslated_cursor_discovery_still_fails_compatibility(self):
        self.assertTrue(sync(self.root, self.upstream, self.new))
        path = self.upstream / 'pstack/agents/poteto-agent.md'
        path.write_text(path.read_text().replace('If no such file exists, stop and tell your parent.',
                                                'If no such file exists, invent a replacement.'))
        before = self.files()
        with self.assertRaisesRegex(SyncConflict, 'validation'):
            sync(self.root, self.upstream, self.commit())
        self.assertEqual(self.files(), before)

    def test_historical_help_renderings_migrate_to_scoped_rules(self):
        name = 'skills/poteto-help/SKILL.md'
        for legacy in self.adaptations[name]['legacy_renderings']:
            with self.subTest(source=legacy['upstream'][:80]):
                result, _ = adapt(legacy['upstream'].encode(), name, self.adaptations)
                self.assertIn(b'## Pick a skill', result)
                self.assertNotIn(b'~/.cursor/', result)
                self.assertNotIn(b'subagent_type:', result)


if __name__ == '__main__':
    unittest.main()
