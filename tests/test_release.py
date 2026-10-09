import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/release.sh'


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        plugin = self.root / 'plugins/pstack-for-codex'
        plugin.mkdir(parents=True)
        (plugin / 'plugin.json').write_text(json.dumps({'version': '1.0.2'}))
        (self.root / 'upstream.json').write_text(json.dumps({'commit': 'a' * 40}))
        (self.root / 'README.md').write_text('release snapshot')
        self.git('init', '-q')
        self.git('config', 'user.email', 'fixture@example.com')
        self.git('config', 'user.name', 'Fixture')
        self.git('add', '.')
        self.git('commit', '-qm', 'fixture')
        self.commit = self.git('rev-parse', 'HEAD').strip()
        self.git('remote', 'add', 'origin', str(self.root))
        mock = self.root / 'bin/gh'
        mock.parent.mkdir()
        mock.write_text(f'#!{sys.executable}\n' + '''import hashlib, json, os, sys, zipfile
from pathlib import Path
args = sys.argv[1:]
with open(os.environ['GH_TEST_LOG'], 'a') as log:
    log.write(json.dumps(args) + '\\n')
if args[:2] == ['release', 'view']:
    if 'targetCommitish' in args:
        print(os.environ['GH_TEST_COMMIT'])
    else:
        state = os.environ['GH_TEST_STATE']
        if state == 'missing':
            sys.exit(1)
        print(state)
elif args[:2] == ['release', 'upload']:
    archive, checksum = map(Path, args[3:5])
    assert checksum.read_text() == hashlib.sha256(archive.read_bytes()).hexdigest() + '  ' + archive.name + '\\n'
    with zipfile.ZipFile(archive) as package:
        assert package.testzip() is None
        assert package.read('pstack-for-codex-1.0.2/README.md') == b'release snapshot'
    if os.environ.get('GH_TEST_FAIL_UPLOAD'):
        sys.exit(1)
''')
        mock.chmod(0o755)
        self.log = self.root / 'gh.jsonl'
        self.env = dict(os.environ, PATH=f'{mock.parent}:{os.environ["PATH"]}',
                        GH_TEST_LOG=str(self.log), GH_TEST_STATE='missing',
                        GH_TEST_COMMIT=self.commit)

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], text=True)

    def run_release(self):
        result = subprocess.run(['bash', str(SCRIPT)], cwd=self.root,
                                env=self.env, capture_output=True, text=True)
        calls = [json.loads(line) for line in self.log.read_text().splitlines()]
        return result, calls

    def test_new_release_uses_manifest_version_and_exact_commit(self):
        result, calls = self.run_release()
        self.assertEqual(result.returncode, 0, result.stderr)
        create = next(call for call in calls if call[:2] == ['release', 'create'])
        self.assertEqual(create[2], 'v1.0.2')
        self.assertEqual(create[create.index('--target') + 1], self.commit)
        self.assertIn('--draft', create)
        self.assertEqual([call[1] for call in calls], ['view', 'create', 'upload', 'edit'])
        self.assertIn('--draft=false', calls[-1])

    def test_published_release_is_skipped(self):
        self.env['GH_TEST_STATE'] = 'false'
        result, calls = self.run_release()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([call[1] for call in calls], ['view'])

    def test_draft_resumes_from_original_commit_after_head_changes(self):
        self.env['GH_TEST_STATE'] = 'true'
        (self.root / 'README.md').write_text('later documentation')
        self.git('add', 'README.md')
        self.git('commit', '-qm', 'later docs')
        result, calls = self.run_release()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([call[1] for call in calls], ['view', 'view', 'upload', 'edit'])

    def test_upload_failure_does_not_publish(self):
        self.env['GH_TEST_FAIL_UPLOAD'] = '1'
        result, calls = self.run_release()
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('edit', [call[1] for call in calls])


if __name__ == '__main__':
    unittest.main()
