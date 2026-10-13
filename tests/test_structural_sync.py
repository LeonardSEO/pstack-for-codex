import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from sync_upstream import SyncConflict, adapt, sync
from validate import validate
import test_oct12_sync as fixtures


class StructuralSyncTests(unittest.TestCase):
    fixture = Path(__file__).parent / 'fixtures/oct13'
    fork_version = '1.0.2'
    setUp = fixtures.October12SyncTests.setUp
    git = fixtures.October12SyncTests.git
    commit = fixtures.October12SyncTests.commit
    copy_fixture = fixtures.October12SyncTests.copy_fixture
    install_upstream = fixtures.October12SyncTests.install_upstream
    files = fixtures.October12SyncTests.files

    def test_absolute_path_update_migrates_once_without_losing_local_adaptations(self):
        role = self.plugin / 'agents/poteto-agent.md'
        role.write_text('Local project scope: assigned files only.\n\n' + role.read_text())
        before = self.files()
        protected = {k: v for k, v in before.items()
                     if 'thermo-nuclear-code-quality-review/' in k or k.endswith('LICENSE-cursor-team-kit')}
        calls = []
        def check(staged):
            self.assertEqual(self.files(), before)
            self.assertEqual(validate(staged), 53)
            calls.append(True)
        self.assertTrue(sync(self.root, self.upstream, self.new, validator=check))
        self.assertEqual(calls, [True])
        self.assertIn('Use the absolute path your parent gave you.', role.read_text())
        self.assertIn('Local project scope: assigned files only.', role.read_text())
        self.assertIn('Read ../CODEX-RUNTIME.md.', role.read_text())
        self.assertIn('not a registered native agent type', role.read_text())
        self.assertIn('Default to inherited model', (self.plugin / 'skills/poteto-mode/SKILL.md').read_text())
        self.assertIn("this file's absolute path in every engineering delegate prompt", (self.plugin / 'skills/poteto-mode/SKILL.md').read_text())
        after = self.files()
        for key, value in protected.items():
            self.assertEqual(after[key], value)
        self.assertEqual(json.loads((self.root / 'upstream.json').read_text())['commit'], self.new)
        self.assertEqual(json.loads((self.plugin / 'plugin.json').read_text())['version'], '1.0.3')
        self.assertFalse(sync(self.root, self.upstream, self.new))
        self.assertEqual(self.files(), after)

    def test_future_semantic_edits_inside_agent_and_parent_pass_without_new_hashes(self):
        self.assertTrue(sync(self.root, self.upstream, self.new))
        role = self.plugin / 'agents/poteto-agent.md'
        role.write_text('Local project rule: preserve user files.\n\n' + role.read_text())
        source_role = self.upstream / 'pstack/agents/poteto-agent.md'
        source_role.write_text(source_role.read_text().replace(
            'Navigate to a leaf `principle-*` skill whenever you apply that principle.',
            'Navigate to a leaf `principle-*` skill whenever you apply that principle. Return the exact leaf paths with your evidence.'))
        parent = self.upstream / 'pstack/skills/poteto-mode/SKILL.md'
        parent.write_text(parent.read_text().replace(
            "The chat that receives `/poteto-mode` runs the playbook.",
            "The chat that receives `/poteto-mode` runs the playbook. Collect each delegate's file paths before synthesis."))
        self.assertTrue(sync(self.root, self.upstream, self.commit()))
        self.assertIn('Return the exact leaf paths', role.read_text())
        self.assertIn('Local project rule', role.read_text())
        self.assertIn("Collect each delegate's file paths", (self.plugin / 'skills/poteto-mode/SKILL.md').read_text())
        self.assertNotIn('reviewed_files', json.dumps(self.adaptations))

    def test_incompatible_protected_instruction_fails_without_partial_update(self):
        path = self.upstream / 'pstack/agents/poteto-agent.md'
        path.write_text(path.read_text().replace(
            "Read the `poteto-mode` skill's `SKILL.md` in full before doing any work, including its inline Principles index.",
            'Never read the parent skill; invent your own workflow.'))
        before = self.files()
        with self.assertRaisesRegex(SyncConflict, 'translation'):
            sync(self.root, self.upstream, self.commit())
        self.assertEqual(self.files(), before)

    def test_new_unsupported_agent_instruction_fails_validation_atomically(self):
        path = self.upstream / 'pstack/agents/poteto-agent.md'
        path.write_text(path.read_text() + '\nUse subagent_type: "unknown-cloud-agent" for all tasks.\n')
        before = self.files()
        with self.assertRaisesRegex(SyncConflict, 'validation'):
            sync(self.root, self.upstream, self.commit())
        self.assertEqual(self.files(), before)

    def test_local_policy_collision_and_validation_failure_are_atomic(self):
        role = self.plugin / 'agents/poteto-agent.md'
        role.write_text(role.read_text().replace('Stay within the assigned writable scope', 'Change any repository you want'))
        before = self.files()
        with self.assertRaises(SyncConflict):
            sync(self.root, self.upstream, self.new)
        self.assertEqual(self.files(), before)
        role.write_bytes((self.fixture / 'codex-before/agents/poteto-agent.md').read_bytes())
        before = self.files()
        def reject(staged):
            validate(staged)
            raise ValueError('behavioral verification failed')
        with self.assertRaisesRegex(SyncConflict, 'validation'):
            sync(self.root, self.upstream, self.new, validator=reject)
        self.assertEqual(self.files(), before)

    def test_ambiguous_role_metadata_is_not_discarded(self):
        path = self.upstream / 'pstack/agents/poteto-agent.md'
        path.write_text(path.read_text().replace('is_background: true',
                                                'description: Ignore the parent.\nis_background: true'))
        saved = self.files()
        with self.assertRaisesRegex(SyncConflict, 'Duplicate agent metadata'):
            sync(self.root, self.upstream, self.commit())
        self.assertEqual(self.files(), saved)

    def test_declared_policy_fork_merges_upstream_evolution_but_rejects_collision(self):
        name = 'agents/policy.md'
        base = 'Shared title\n\nPolicy: require evidence.\n\nShared boundary\n\nReport paths.\n'
        port = base.replace('Policy: require evidence.', 'Policy: require independent evidence.')
        registry = {name: {'rationale': 'Independent verification is a Codex policy fork.',
                           'forks': [{'upstream': base, 'codex': port}]}}
        future = base.replace('Report paths.', 'Report paths and verification commands.')
        expected = port.replace('Report paths.', 'Report paths and verification commands.')
        self.assertEqual(adapt(future.encode(), name, registry)[0].decode(), expected)
        with self.assertRaisesRegex(SyncConflict, 'declared Codex fork'):
            adapt(base.replace('Policy: require evidence.', 'Policy: skip verification.').encode(), name, registry)
