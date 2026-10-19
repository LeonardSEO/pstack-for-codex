"""Publish a validated upstream snapshot, rebuilding if main races the push."""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def sync(root, upstream, ref, report):
    # Use the scripts from the freshly fetched main on every attempt.
    path = root.parent / 'candidate-report.json'
    result = subprocess.run([sys.executable, str(root / 'scripts/sync_upstream.py'),
                             '--repo', str(root), '--upstream-dir', str(upstream),
                             '--ref', ref, '--report', str(path)], capture_output=True, text=True)
    if path.exists():
        report.update(json.loads(path.read_text()))
    if result.returncode:
        raise RuntimeError(f'Synchronization failed:\n{result.stdout}\n{result.stderr}')
    return report['status'] == 'UPDATED'


def release(root):
    result = subprocess.run(['bash', 'scripts/release.sh'], cwd=root, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f'Release failed:\n{result.stdout}\n{result.stderr}')
    return result.stdout.strip()


def publish(root, upstream, ref, report=None):
    root, upstream = Path(root).resolve(), Path(upstream).resolve()
    report = report if report is not None else {}
    report.update(push_status='not attempted', release_status='not attempted')
    for attempt in range(1, 4):
        report['attempt'] = attempt
        git(root, 'fetch', 'origin', 'main')
        base = git(root, 'rev-parse', 'refs/remotes/origin/main')
        with tempfile.TemporaryDirectory(prefix='pstack-publish-') as tmp:
            candidate = Path(tmp) / 'checkout'
            git(root, 'worktree', 'add', '--detach', str(candidate), base)
            try:
                sync(candidate, upstream, ref, report=report)
                git(candidate, 'add', '--force', '--all', '--', 'plugins/pstack-for-codex', 'upstream.json')
                changed = subprocess.run(['git', '-C', str(candidate), 'diff', '--cached', '--quiet']).returncode
                if changed not in (0, 1):
                    raise RuntimeError('Unable to inspect staged package')
                if changed:
                    git(candidate, '-c', 'user.name=github-actions[bot]',
                        '-c', 'user.email=41898282+github-actions[bot]@users.noreply.github.com',
                        'commit', '-m', 'chore: sync authoritative pstack upstream')
                    pushed = subprocess.run(['git', '-C', str(candidate), 'push', 'origin', 'HEAD:main'],
                                            capture_output=True, text=True)
                    if pushed.returncode:
                        git(root, 'fetch', 'origin', 'main')
                        if git(root, 'rev-parse', 'refs/remotes/origin/main') != base:
                            report['push_status'] = 'main changed; rebuilding'
                            continue
                        report['push_status'] = 'failed'
                        raise RuntimeError(f'Git push failed: {pushed.stderr}')
                    report['push_status'] = 'pushed'
                else:
                    # Do not release an old main snapshot when there was no diff.
                    git(root, 'fetch', 'origin', 'main')
                    if git(root, 'rev-parse', 'refs/remotes/origin/main') != base:
                        report['push_status'] = 'main changed; rebuilding'
                        continue
                    report['push_status'] = 'unchanged'
                report['published_commit'] = git(candidate, 'rev-parse', 'HEAD')
                report['release_status'] = 'running'
                report['release_status'] = release(candidate)
                return report
            finally:
                git(root, 'worktree', 'remove', '--force', str(candidate))
    raise RuntimeError('Main changed during all three push attempts; retry the workflow')


def write_report(report, path):
    path.write_text(json.dumps(report, indent=2) + '\n')
    lines = ['## Daily pstack synchronization', '',
             f"- Result: {report.get('status', 'ERROR')}",
             f"- Source: `{report.get('source_commit', 'unavailable')}`",
             f"- Package: +{report.get('added', 0)} added, ~{report.get('modified', 0)} modified, -{report.get('deleted', 0)} deleted",
             f"- Push: {report.get('push_status')}",
             f"- Main commit: `{report.get('published_commit', 'not published')}`",
             f"- Release: {report.get('release_status')}",
             f"- Attempt: {report.get('attempt', 0)}/3", '']
    if report.get('error'):
        lines += ['### Error', '', '```text', report['error'], '```', '']
    warnings = report.get('warnings', [])
    lines += [f'### Content warnings ({len(warnings)})', '',
              'These do not block publication. The Codex runtime contract remains authoritative.', '']
    lines += ['- ' + w.replace('\n', ' ') for w in warnings]
    markdown = '\n'.join(lines) + '\n'
    path.with_suffix('.md').write_text(markdown)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as summary:
            summary.write(markdown)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--upstream-dir', type=Path, required=True)
    parser.add_argument('--ref', default='HEAD')
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    report = {}
    try:
        publish(args.repo, args.upstream_dir, args.ref, report)
    except Exception as error:
        report.update(status='ERROR', error=str(error))
        raise
    finally:
        write_report(report, args.report)
    print(f"{report['status']}: {report['push_status']}; {report['release_status']}")


if __name__ == '__main__':
    main()
