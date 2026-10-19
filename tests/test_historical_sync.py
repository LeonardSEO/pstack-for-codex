"""Replay real source fragments from failed October 11–19 synchronization runs."""
import hashlib
import json
from pathlib import Path

import unittest
from test_authoritative_sync import SyncFixture, PROJECT
from sync_upstream import sync, target_path


class HistoricalReplayTests(SyncFixture, unittest.TestCase):
    def test_recorded_upstream_intervals_overwrite_every_local_rewrite(self):
        for fixture_name in ['arena', 'oct12', 'oct13', 'oct13-latest', 'oct14']:
            fixture = PROJECT / 'tests/fixtures' / fixture_name
            with self.subTest(interval=fixture_name):
                manifest_path = fixture / 'manifest.json'
                if manifest_path.exists():
                    manifest = json.loads(manifest_path.read_text())
                    for name, versions in manifest['files'].items():
                        metadata = versions.get('upstream-after')
                        if metadata:
                            data = (fixture / 'upstream-after' / name).read_bytes()
                            self.assertEqual(hashlib.sha256(data).hexdigest(), metadata['sha256'])
                            self.source(name, data).chmod(metadata['mode'])
                else:
                    self.source('skills/arena/SKILL.md', (fixture / 'upstream-after.md').read_bytes())
                head = self.commit()
                for name in ['agents/comment-sicko.md', 'agents/poteto-agent.md',
                             'skills/arena/SKILL.md', 'skills/poteto-help/SKILL.md']:
                    local = self.plugin / name
                    local.parent.mkdir(parents=True, exist_ok=True)
                    local.write_text('Incompatible local rewrite\n')
                report = {}
                self.assertTrue(sync(self.root, self.upstream, head, report=report))
                for name in ['agents/comment-sicko.md', 'agents/poteto-agent.md',
                             'skills/arena/SKILL.md', 'skills/poteto-help/SKILL.md']:
                    local = self.plugin / name
                    if local.exists():
                        self.assertNotIn('Incompatible local rewrite', local.read_text())
                after = self.files()
                self.assertFalse(sync(self.root, self.upstream, head))
                self.assertEqual(self.files(), after)

    def test_setup_and_principles_edits_both_replace_compact_guides(self):
        for name in ['docs/guide/01-setup.md', 'docs/guide/08-principles.md']:
            self.source(name, '# Upstream guide\n\n[section](#new-anchor)\n')
            target = self.plugin / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('# Codex guide\n\nSee runtime contract.\n')
        sync(self.root, self.upstream, self.commit())
        for name in ['docs/guide/01-setup.md', 'docs/guide/08-principles.md']:
            self.assertEqual((self.plugin / name).read_bytes(), (self.upstream / 'pstack' / name).read_bytes())

    def test_real_october_15_through_19_guides_are_copied_without_conflict(self):
        fixture = PROJECT / 'tests/fixtures/oct15-19'
        for record in json.loads((fixture / 'manifest.json').read_text()):
            with self.subTest(date=record['date'], commit=record['commit']):
                for name, digest in record['files'].items():
                    data = (fixture / record['date'] / name).read_bytes()
                    self.assertEqual(hashlib.sha256(data).hexdigest(), digest)
                    self.source(name, data)
                    local = self.plugin / name
                    local.parent.mkdir(parents=True, exist_ok=True)
                    local.write_text('Conflicting Codex rewrite')
                head = self.commit()
                sync(self.root, self.upstream, head)
                for name in record['files']:
                    self.assertEqual((self.plugin / name).read_bytes(),
                                     (fixture / record['date'] / name).read_bytes())
                self.assertFalse(sync(self.root, self.upstream, head))
