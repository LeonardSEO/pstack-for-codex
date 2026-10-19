import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / 'scripts'))
from sync_upstream import sync, adapt, SyncConflict
from validate import validate


class SyncFixture:

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'fork'
        self.upstream = Path(self.tmp.name) / 'source'
        self.upstream.mkdir()
        for directory in ['plugins', 'schemas', '.agents']:
            shutil.copytree(PROJECT / directory, self.root / directory)
        self.plugin = self.root / 'plugins/pstack-for-codex'
        self.git('init', '-q')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.com')
        self.source('.cursor-plugin/plugin.json', '{"version":"0.15.24"}')
        self.source('LICENSE', 'Upstream license\n')
        self.source('skills/example/SKILL.md', '---\nname: upstream\ndescription: Example skill\n---\n\nSource instructions.\n')
        self.source('assets/logo.png', b'upstream asset')
        self.source('docs/guide/01-setup.md', 'Upstream setup\n')
        self.old = self.commit()
        (self.root / 'upstream.json').write_text(json.dumps({'commit': self.old}))

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.upstream), *args], text=True).strip()

    def source(self, name, value):
        path = self.upstream / 'pstack' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value.encode() if isinstance(value, str) else value)
        return path

    def commit(self):
        self.git('add', '.')
        self.git('commit', '--allow-empty', '-qm', 'fixture')
        return self.git('rev-parse', 'HEAD')

    def files(self):
        return {str(p.relative_to(self.root)): (p.read_bytes(), p.stat().st_mode & 0o777)
                for p in self.root.rglob('*') if p.is_file()}


class AuthoritativeSyncTests(SyncFixture, unittest.TestCase):
    def test_upstream_overwrites_local_content_even_at_same_checkpoint(self):
        target = self.plugin / 'docs/guide/01-setup.md'
        target.write_text('Local incompatible rewrite')
        self.assertTrue(sync(self.root, self.upstream, self.old))
        self.assertEqual(target.read_text(), 'Upstream setup\n')
        before = self.files()
        self.assertFalse(sync(self.root, self.upstream, self.old))
        self.assertEqual(self.files(), before)

    def test_new_directories_binary_modes_and_deletions(self):
        sync(self.root, self.upstream, self.old)
        path = self.source('new-tools/tool.sh', '#!/bin/sh\nexit 0\n')
        path.chmod(0o755)
        self.source('new-tools/data.bin', b'\x00\xff')
        (self.upstream / 'pstack/docs/guide/01-setup.md').unlink()
        self.assertTrue(sync(self.root, self.upstream, self.commit()))
        self.assertEqual((self.plugin / 'new-tools/tool.sh').stat().st_mode & 0o777, 0o755)
        self.assertEqual((self.plugin / 'new-tools/data.bin').read_bytes(), b'\x00\xff')
        self.assertFalse((self.plugin / 'docs/guide/01-setup.md').exists())

    def test_independent_codex_files_survive_upstream_collisions(self):
        protected = ['CODEX-RUNTIME.md', 'LICENSE-cursor-team-kit',
                     'skills/thermo-nuclear-code-quality-review/SKILL.md',
                     'skills/thermo-nuclear-code-quality-review/agents/openai.yaml']
        before = {p: (self.plugin / p).read_bytes() for p in protected}
        for p in protected:
            self.source(p, 'upstream collision')
        sync(self.root, self.upstream, self.commit())
        for p in protected:
            self.assertEqual((self.plugin / p).read_bytes(), before[p])

    def test_host_configuration_is_reference_only(self):
        for path in ['.mcp.json', 'hooks/hooks.json', '.cursor/rules/rule.mdc', 'AGENTS.md',
                     'skills/example/.cursor/rules/policy.mdc', 'skills/example/.claude/settings.json']:
            self.source(path, 'host config')
        self.source('automations/example.md', 'automation reference')
        sync(self.root, self.upstream, self.commit())
        for path in ['.mcp.json', 'hooks/hooks.json', '.cursor/rules/rule.mdc', 'AGENTS.md',
                     'skills/example/.cursor/rules/policy.mdc', 'skills/example/.claude/settings.json']:
            self.assertFalse((self.plugin / path).exists())
            self.assertTrue((self.plugin / 'references-host' / path).exists())
        self.assertTrue((self.plugin / 'references-benny/example.md').exists())

    def test_unknown_instructions_and_broken_links_are_warnings(self):
        self.source('skills/example/SKILL.md', '---\nname: example\ndescription: Example\n---\nUse subagent_type: unknown and [reference](missing.md).\n')
        report = {}
        sync(self.root, self.upstream, self.commit(), report=report)
        self.assertIn('subagent_type:', (self.plugin / 'skills/example/SKILL.md').read_text())
        self.assertTrue(any('unsupported' in w for w in report['warnings']))
        self.assertTrue(any('broken' in w for w in report['warnings']))
        validate(self.root)

    def test_missing_ambiguous_and_overlapping_translations_preserve_source(self):
        for data, rules in [
            (b'new wording', [{'variants': [{'upstream': 'old wording', 'codex': 'translated'}]}]),
            (b'old old', [{'variants': [{'upstream': 'old', 'codex': 'translated'}]}]),
            (b'abcdef', [{'variants': [{'upstream': 'abcd', 'codex': 'A'}]}, {'variants': [{'upstream': 'cdef', 'codex': 'B'}]}]),
        ]:
            warnings = []
            result, _ = adapt(data, 'docs/example.md', {'docs/example.md': {'rules': rules}}, warnings=warnings)
            self.assertEqual(result, data)
            self.assertTrue(warnings)

    def test_known_translation_applies(self):
        result, _ = adapt(b'old', 'docs/example.md', {'docs/example.md': {'rules': [{'variants': [{'upstream': 'old', 'codex': 'new'}]}]}})
        self.assertEqual(result, b'new')

    def test_invalid_source_version_or_missing_tree_never_changes_package(self):
        before = self.files()
        self.source('.cursor-plugin/plugin.json', '{}')
        with self.assertRaises(SyncConflict):
            sync(self.root, self.upstream, self.commit())
        self.assertEqual(self.files(), before)
        with self.assertRaises((SyncConflict, subprocess.CalledProcessError)):
            sync(self.root, self.upstream, 'missing-ref')
        self.assertEqual(self.files(), before)

    def test_invalid_skill_metadata_and_symlink_block_before_write(self):
        before = self.files()
        self.source('skills/example/SKILL.md', 'not skill frontmatter')
        with self.assertRaises(SyncConflict):
            sync(self.root, self.upstream, self.commit())
        self.assertEqual(self.files(), before)
        self.source('skills/example/SKILL.md', '---\nname: example\ndescription: Example\n---\nText')
        (self.upstream / 'pstack/escape').symlink_to('/tmp')
        with self.assertRaises(SyncConflict):
            sync(self.root, self.upstream, self.commit())
        self.assertEqual(self.files(), before)

    def test_staged_validation_failure_is_atomic(self):
        before = self.files()
        def reject(candidate):
            self.assertEqual(self.files(), before)
            raise ValueError('rejected candidate')
        with self.assertRaisesRegex(SyncConflict, 'validation'):
            sync(self.root, self.upstream, self.old, validator=reject)
        self.assertEqual(self.files(), before)

    def test_file_directory_transitions(self):
        self.source('extras/node', 'file')
        sync(self.root, self.upstream, self.commit())
        (self.upstream / 'pstack/extras/node').unlink()
        self.source('extras/node/child', 'child')
        sync(self.root, self.upstream, self.commit())
        self.assertEqual((self.plugin / 'extras/node/child').read_text(), 'child')
        shutil.rmtree(self.upstream / 'pstack/extras/node')
        self.source('extras/node', 'file again')
        sync(self.root, self.upstream, self.commit())
        self.assertEqual((self.plugin / 'extras/node').read_text(), 'file again')

    def test_report_and_version_alignment(self):
        report = {}
        self.source('.cursor-plugin/plugin.json', '{"version":"0.16.0"}')
        head = self.commit()
        sync(self.root, self.upstream, head, report=report)
        self.assertEqual(report['source_commit'], head)
        self.assertEqual(report['status'], 'UPDATED')
        self.assertGreater(report['added'], 0)
        self.assertEqual(json.loads((self.plugin / 'plugin.json').read_text())['version'], '0.16.0')
        self.assertEqual(json.loads((self.root / 'upstream.json').read_text())['commit'], head)

    def test_missing_upstream_skills_is_not_an_empty_success(self):
        shutil.rmtree(self.upstream / 'pstack/skills')
        before = self.files()
        with self.assertRaises(SyncConflict):
            sync(self.root, self.upstream, self.commit())
        self.assertEqual(self.files(), before)
