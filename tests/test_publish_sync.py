import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]


class PublishSyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.remote = self.root / 'remote.git'
        self.checkout = self.root / 'checkout'
        self.git(self.root, 'init', '--bare', '-q', str(self.remote))
        self.git(self.root, 'clone', '-q', str(self.remote), str(self.checkout))
        self.git(self.checkout, 'config', 'user.name', 'Fixture')
        self.git(self.checkout, 'config', 'user.email', 'fixture@example.com')
        self.git(self.checkout, 'checkout', '-qb', 'main')
        plugin = self.checkout / 'plugins/pstack-for-codex'
        plugin.mkdir(parents=True)
        (plugin / 'file.txt').write_text('old')
        (self.checkout / 'upstream.json').write_text('{}')
        self.git(self.checkout, 'add', '.')
        self.git(self.checkout, 'commit', '-qm', 'initial')
        self.git(self.checkout, 'push', '-q', 'origin', 'main')
        self.old = self.git(self.checkout, 'rev-parse', 'HEAD')
        spec = importlib.util.spec_from_file_location('publish_sync', PROJECT / 'scripts/publish_sync.py')
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.calls = []
        self.releases = []

    def git(self, root, *args):
        return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.PIPE, text=True).strip()

    def generate(self, root, upstream, ref, report):
        self.calls.append(root)
        path = root / 'plugins/pstack-for-codex/file.txt'
        changed = path.read_text() != 'new'
        path.write_text('new')
        report.update(status='UPDATED' if changed else 'UNCHANGED', source_commit='a'*40,
                      added=0, modified=int(changed), deleted=0, warnings=[])
        return changed

    def release(self, root):
        self.releases.append(self.git(root, 'rev-parse', 'HEAD'))
        return 'published or already exists'

    def test_direct_push_and_repeat_without_empty_commit(self):
        with patch.object(self.module, 'sync', self.generate), patch.object(self.module, 'release', self.release):
            first = self.module.publish(self.checkout, self.root, 'HEAD')
            new = self.git(self.remote, 'rev-parse', 'main')
            self.assertNotEqual(new, self.old)
            self.assertEqual(first['push_status'], 'pushed')
            self.assertEqual(self.releases, [new])
            second = self.module.publish(self.checkout, self.root, 'HEAD')
            self.assertEqual(self.git(self.remote, 'rev-parse', 'main'), new)
            self.assertEqual(second['push_status'], 'unchanged')
            self.assertEqual(self.git(self.checkout, 'rev-parse', 'HEAD'), self.old)

    def test_racing_main_is_rebuilt_without_losing_other_commit(self):
        counter = 0
        original = self.generate
        def racing(root, upstream, ref, report):
            nonlocal counter
            counter += 1
            if counter == 1:
                (self.checkout / 'unrelated.txt').write_text('other contributor')
                self.git(self.checkout, 'add', 'unrelated.txt')
                self.git(self.checkout, 'commit', '-qm', 'concurrent change')
                self.git(self.checkout, 'push', '-q', 'origin', 'main')
            return original(root, upstream, ref, report)
        with patch.object(self.module, 'sync', racing), patch.object(self.module, 'release', self.release):
            report = self.module.publish(self.checkout, self.root, 'HEAD')
        self.assertEqual(report['attempt'], 2)
        self.assertEqual(self.git(self.remote, 'show', 'main:unrelated.txt'), 'other contributor')
        self.assertEqual(len(self.releases), 1)

    def test_push_denied_is_not_retried_or_released(self):
        hook = self.remote / 'hooks/pre-receive'
        hook.write_text('#!/bin/sh\nexit 1\n'); hook.chmod(0o755)
        with patch.object(self.module, 'sync', self.generate), patch.object(self.module, 'release', self.release):
            with self.assertRaisesRegex(RuntimeError, 'push'):
                self.module.publish(self.checkout, self.root, 'HEAD')
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.releases, [])
        self.assertEqual(self.git(self.remote, 'rev-parse', 'main'), self.old)

    def test_continuously_racing_main_stops_after_three_attempts(self):
        original = self.generate
        def racing(root, upstream, ref, report):
            (self.checkout / 'unrelated.txt').write_text(str(len(self.calls)))
            self.git(self.checkout, 'add', 'unrelated.txt')
            self.git(self.checkout, 'commit', '-qm', 'concurrent change')
            self.git(self.checkout, 'push', '-q', 'origin', 'main')
            return original(root, upstream, ref, report)
        with patch.object(self.module, 'sync', racing), patch.object(self.module, 'release', self.release):
            with self.assertRaisesRegex(RuntimeError, 'three'):
                self.module.publish(self.checkout, self.root, 'HEAD')
        self.assertEqual(len(self.calls), 3)
        self.assertEqual(self.releases, [])


from test_authoritative_sync import SyncFixture
import shutil


class CompletePackagePublicationTests(SyncFixture, unittest.TestCase):
    def test_real_sync_publishes_source_files_ignored_by_fork(self):
        self.source('extras/tracked.pyc', b'upstream-tracked-bytes')
        self.commit()
        shutil.copytree(PROJECT / 'scripts', self.root / 'scripts')
        (self.root / '.gitignore').write_text('*.pyc\n')
        remote = self.root.parent / 'remote.git'
        def run(*args):
            return subprocess.check_output(['git', '-C', str(self.root), *args], text=True, stderr=subprocess.PIPE).strip()
        run('init', '-q', '-b', 'main')
        run('config', 'user.name', 'Fixture')
        run('config', 'user.email', 'fixture@example.com')
        run('add', '.')
        run('commit', '-qm', 'initial')
        run('init', '--bare', '-q', str(remote))
        run('remote', 'add', 'origin', str(remote))
        run('push', '-q', 'origin', 'main')
        spec = importlib.util.spec_from_file_location('publish_sync', PROJECT / 'scripts/publish_sync.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch.object(module, 'release', lambda root: 'test: external release skipped'):
            result = module.publish(self.root, self.upstream, 'HEAD')
        self.assertEqual(result['push_status'], 'pushed')
        contents = subprocess.check_output(['git', '-C', str(remote), 'show',
                                           'main:plugins/pstack-for-codex/extras/tracked.pyc'])
        self.assertEqual(contents, b'upstream-tracked-bytes')
