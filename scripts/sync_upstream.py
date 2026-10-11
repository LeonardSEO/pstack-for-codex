import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path, PurePosixPath

import yaml

from validate import validate


# This cursor-team-kit import is maintained separately from pstack, even if
# pstack later introduces or removes a skill with the same name.
PRESERVED_SKILL_PATH = 'skills/thermo-nuclear-code-quality-review'
ADAPTATIONS_PATH = Path(__file__).with_name('codex_adaptations.json')
SKILL_PATH = re.compile(r'skills/[^/]+/SKILL.md')


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
    try:
        front = yaml.safe_load(parts[1])
    except yaml.YAMLError as error:
        raise SyncConflict(f'Invalid skill frontmatter: {name}') from error
    if not isinstance(front, dict) or not isinstance(front.get('description'), str):
        raise SyncConflict(f'Missing skill description: {name}')
    skill_name = PurePosixPath(name).parent.name
    body = parts[2].lstrip()
    if 'CODEX-RUNTIME.md' not in body:
        body = ('Read [Codex runtime contract](../../CODEX-RUNTIME.md) before applying this workflow. '
                'It governs tools, delegation, models, authorization and fallbacks.\n\n\n' + body)
    header = yaml.safe_dump({'name': skill_name, 'description': front['description']}, sort_keys=False).strip()
    return f'---\n{header}\n---\n\n{body}'.encode()


def adapt(data, name, adaptations, required=()):
    """Render known upstream instructions for Codex before a three-way merge.

    Exact, reviewed source fragments make translations deterministic. An edited
    translation input must be reviewed rather than silently replacing new policy.
    The live fork is never used to manufacture this merge base.
    """
    if SKILL_PATH.fullmatch(name):
        data = normalize_skill(data, name)
    entry = adaptations.get(name, {})
    digest = hashlib.sha256(data).hexdigest()
    if 'reviewed_files' in entry:
        if digest not in entry['reviewed_files']:
            raise SyncConflict(f'Unreviewed change to a Codex rewrite: {name}')
        return entry['reviewed_files'][digest].encode(), set()
    active = set()
    # Match all inputs against the same source, so one translation cannot trigger
    # another translation or accidentally consume its output.
    replacements = []
    for index, rule in enumerate(entry.get('rules', [])):
        matches = [variant for variant in rule['variants']
                   if variant['upstream'].encode() in data]
        if len(matches) > 1:
            raise SyncConflict(f'Ambiguous Codex translation {index + 1}: {name}')
        if matches:
            source = matches[0]['upstream'].encode()
            if not source or data.count(source) != 1:
                raise SyncConflict(f'Ambiguous Codex translation {index + 1}: {name}')
            start = data.index(source)
            replacements.append((start, start + len(source), matches[0]['codex'].encode()))
            active.add(index)
        elif index in required and digest not in rule.get('reviewed_absence', []):
            raise SyncConflict(f'Upstream changed Codex translation {index + 1}: {name}')
    end = 0
    rendered = []
    for start, stop, replacement in sorted(replacements):
        if start < end:
            raise SyncConflict(f'Overlapping Codex translations: {name}')
        rendered.extend((data[end:start], replacement))
        end = stop
    rendered.append(data[end:])
    return b''.join(rendered), active


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


def write_changes(changes, root, destination):
    for target in changes:
        path = destination / target.relative_to(root)
        parents = target.relative_to(root).parents
        if path.is_symlink() or any((destination / parent).is_symlink()
                                    for parent in parents if parent != Path('.')):
            raise SyncConflict(f'Cannot write through a fork symlink: {target.relative_to(root)}')
    for target, value in changes.items():
        path = destination / target.relative_to(root)
        if value is None:
            if path.exists():
                path.unlink()
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(value[0])
            os.chmod(path, value[1])


def validate_candidate(root, validator):
    try:
        validator(root)
    except Exception as error:
        raise SyncConflict(f'Proposed package failed validation: {error}') from error


def sync(root, upstream, ref, validator=validate):
    root, upstream = Path(root), Path(upstream)
    state_path = root / 'upstream.json'
    state = json.loads(state_path.read_text())
    head = git(upstream, 'rev-parse', f'{ref}^{{commit}}').decode().strip()
    old = snapshot(upstream, state['commit'])
    new = snapshot(upstream, head)
    if old == new:
        if validator is not None:
            validate_candidate(root, validator)
        return False
    plugin = root / 'plugins/pstack-for-codex'
    adaptations = json.loads(ADAPTATIONS_PATH.read_text())
    changes = {}
    for name in sorted(old.keys() | new.keys()):
        if old.get(name) == new.get(name):
            continue
        target = plugin / target_path(name)
        current = target.read_bytes() if target.is_file() else None
        before = old[name][0] if name in old else None
        after = new[name][0] if name in new else None
        required = set()
        if before is not None:
            before, required = adapt(before, name, adaptations)
        if after is not None:
            after, _ = adapt(after, name, adaptations, required)
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
        if SKILL_PATH.fullmatch(name):
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
    if validator is not None:
        with tempfile.TemporaryDirectory() as tmp:
            staged = Path(tmp) / 'candidate'
            def ignore_checkout(directory, names):
                if Path(directory).resolve() == root.resolve():
                    return set(names) & {'.git', '.upstream'}
                return set()
            shutil.copytree(root, staged, symlinks=True,
                            ignore=ignore_checkout)
            write_changes(changes, root, staged)
            validate_candidate(staged, validator)
    write_changes(changes, root, root)
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
