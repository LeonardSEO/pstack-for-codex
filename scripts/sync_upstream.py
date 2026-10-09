import argparse
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path, PurePosixPath

import yaml


# This cursor-team-kit import is maintained separately from pstack, even if
# pstack later introduces or removes a skill with the same name.
PRESERVED_SKILL_PATH = 'skills/thermo-nuclear-code-quality-review'


class SyncConflict(RuntimeError):
    pass


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.PIPE)


def snapshot(repo, ref):
    try:
        entries = git(repo, 'ls-tree', '-rz', f'{ref}:pstack')
    except subprocess.CalledProcessError as error:
        raise SyncConflict('Upstream pstack tree is missing or inaccessible') from error
    result = {}
    for entry in entries.split(b'\0'):
        if not entry:
            continue
        metadata, path = entry.split(b'\t', 1)
        mode, kind, oid = metadata.split()
        name = path.decode('utf-8')
        if name == PRESERVED_SKILL_PATH or name.startswith(PRESERVED_SKILL_PATH + '/'):
            continue
        if mode not in (b'100644', b'100755') or kind != b'blob':
            raise SyncConflict(f'Unsupported upstream file mode: {name}')
        if '..' in PurePosixPath(name).parts or name.startswith('/'):
            raise SyncConflict(f'Unsafe path: {name}')
        if name.startswith(('skills/', 'agents/', 'assets/', 'docs/', 'automations/')) or name == 'LICENSE':
            result[name] = (git(repo, 'cat-file', 'blob', oid.decode()), int(mode, 8) & 0o777)
    return result


def target_path(name):
    return name.replace('automations/', 'references-benny/', 1) if name.startswith('automations/') else name


def normalize_skill(data, name):
    text = data.decode('utf-8')
    parts = text.split('---', 2)
    if len(parts) != 3 or parts[0].strip():
        raise SyncConflict(f'Invalid skill frontmatter: {name}')
    front = yaml.safe_load(parts[1])
    if not isinstance(front, dict) or not isinstance(front.get('description'), str):
        raise SyncConflict(f'Missing skill description: {name}')
    skill_name = PurePosixPath(name).parent.name
    body = parts[2].lstrip()
    if 'CODEX-RUNTIME.md' not in body:
        body = 'Read [Codex runtime contract](../../CODEX-RUNTIME.md) before applying this workflow.\n\n' + body
    header = yaml.safe_dump({'name': skill_name, 'description': front['description']}, sort_keys=False).strip()
    return f'---\n{header}\n---\n\n{body}'.encode()


def merge(current, base, incoming, name):
    if current == base or current == incoming:
        return incoming
    if b'\0' in current + base + incoming:
        raise SyncConflict(f'Binary file modified on both sides: {name}')
    with tempfile.TemporaryDirectory() as tmp:
        paths = []
        for label, content in [('codex', current), ('base', base), ('upstream', incoming)]:
            p = Path(tmp) / label
            p.write_bytes(content)
            paths.append(str(p))
        run = subprocess.run(['git', 'merge-file', '-p', *paths], capture_output=True)
        if run.returncode:
            raise SyncConflict(f'Conflicting upstream and Codex edits: {name}')
        return run.stdout


def sync(root, upstream, ref):
    root, upstream = Path(root), Path(upstream)
    state_path = root / 'upstream.json'
    state = json.loads(state_path.read_text())
    head = git(upstream, 'rev-parse', f'{ref}^{{commit}}').decode().strip()
    old = snapshot(upstream, state['commit'])
    new = snapshot(upstream, head)
    if old == new:
        return False
    plugin = root / 'plugins/pstack-for-codex'
    changes = {}
    for name in sorted(old.keys() | new.keys()):
        if old.get(name) == new.get(name):
            continue
        target = plugin / target_path(name)
        current = target.read_bytes() if target.is_file() else None
        before = old[name][0] if name in old else None
        after = new[name][0] if name in new else None
        if after is None:
            if current is not None and current != before:
                raise SyncConflict(f'Upstream deleted a Codex-modified file: {name}')
            changes[target] = None
            continue
        if before is None:
            if current is not None and current != after:
                raise SyncConflict(f'New upstream file collides with fork file: {name}')
            content = after
        elif current is None:
            raise SyncConflict(f'Upstream changed a locally deleted file: {name}')
        else:
            content = merge(current, before, after, name)
        if re.fullmatch(r'skills/[^/]+/SKILL.md', name):
            content = normalize_skill(content, name)
            meta = target.parent / 'agents/openai.yaml'
            if not meta.exists():
                skill_name = target.parent.name
                changes[meta] = (yaml.safe_dump({'interface': {'display_name': skill_name.replace('-', ' ').title(), 'short_description': 'Engineering workflow for Codex', 'default_prompt': f'Use ${skill_name} for this task.'}, 'policy': {'allow_implicit_invocation': False}}, sort_keys=False).encode(), 0o644)
        changes[target] = (content, new[name][1])
    manifest_path = plugin / 'plugin.json'
    manifest = json.loads(manifest_path.read_text())
    major, minor, patch = map(int, manifest['version'].split('.'))
    manifest['version'] = f'{major}.{minor}.{patch + 1}'
    state['commit'] = head
    changes[manifest_path] = ((json.dumps(manifest, indent=2) + '\n').encode(), 0o644)
    changes[state_path] = ((json.dumps(state, indent=2) + '\n').encode(), 0o644)
    for path, value in changes.items():
        if value is None:
            if path.exists():
                path.unlink()
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(value[0])
            os.chmod(path, value[1])
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--upstream-dir', type=Path, required=True)
    parser.add_argument('--ref', default='HEAD')
    args = parser.parse_args()
    try:
        print('UPDATED' if sync(args.repo, args.upstream_dir, args.ref) else 'UNCHANGED')
    except SyncConflict as error:
        parser.exit(1, f'Sync blocked: {error}\n')
