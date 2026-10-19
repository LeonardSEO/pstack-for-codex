"""Rebuild the Codex package from an authoritative, complete upstream Git tree."""
import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path, PurePosixPath

import yaml
from validate import validate

PRESERVED_SKILL_PATH = 'skills/thermo-nuclear-code-quality-review'
ADAPTATIONS_PATH = Path(__file__).with_name('codex_adaptations.json')
SKILL_PATH = re.compile(r'skills/[^/]+/SKILL.md')
OWNED_FILES = {'plugin.json', 'CODEX-RUNTIME.md', 'LICENSE-cursor-team-kit'}
HOST_FILES = {'AGENTS.md', 'CLAUDE.md', 'GEMINI.md', 'plugin.json', 'mcp.json'}


class SyncConflict(RuntimeError):
    """A source, filesystem or package-structure error (not a text conflict)."""


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.PIPE)


def snapshot(repo, ref):
    # Read committed blobs, never a possibly incomplete sparse working tree.
    try:
        entries = git(repo, 'ls-tree', '-rz', f'{ref}:pstack')
        result = {}
        for entry in entries.split(b'\0'):
            if not entry:
                continue
            metadata, raw_path = entry.split(b'\t', 1)
            mode, kind, oid = metadata.split()
            name = raw_path.decode('utf-8')
            if mode not in (b'100644', b'100755') or kind != b'blob':
                raise SyncConflict(f'Unsupported upstream file mode: {name}')
            parts = PurePosixPath(name).parts
            if '..' in parts or name.startswith('/') or '.git' in parts or '\\' in name:
                raise SyncConflict(f'Unsafe path: {name}')
            result[name] = (git(repo, 'cat-file', 'blob', oid.decode()), int(mode, 8) & 0o777)
        if not result:
            raise SyncConflict('Upstream pstack tree is empty')
        return result
    except (subprocess.CalledProcessError, UnicodeError) as error:
        raise SyncConflict('Upstream pstack tree or blob is missing or inaccessible') from error


def preserved(name):
    return name in OWNED_FILES or name == PRESERVED_SKILL_PATH or name.startswith(PRESERVED_SKILL_PATH + '/')


def target_path(name):
    parts = PurePosixPath(name).parts
    if name.startswith('automations/'):
        return 'references-benny/' + name[len('automations/'):]
    if (any(part.startswith('.') for part in parts) or 'hooks' in parts[:-1]
            or parts[-1] in HOST_FILES or parts[-1] in {'.mcp.json', '.cursorrules'}):
        return 'references-host/' + name
    return name


def normalize_skill(data, name):
    try:
        parts = data.decode('utf-8').split('---', 2)
        if len(parts) != 3 or parts[0].strip():
            raise ValueError('missing frontmatter')
        front = yaml.safe_load(parts[1])
        if not isinstance(front, dict) or not isinstance(front.get('description'), str) or not front['description'].strip():
            raise ValueError('missing description')
    except (ValueError, UnicodeError, yaml.YAMLError) as error:
        raise SyncConflict(f'Invalid skill frontmatter: {name}') from error
    body = parts[2].lstrip()
    preamble = ('Read [Codex runtime contract](../../CODEX-RUNTIME.md) before applying this workflow. '
                'It governs tools, delegation, models, authorization and fallbacks.')
    if not body.startswith(preamble):
        body = preamble + '\n\n' + body
    header = yaml.safe_dump({'name': PurePosixPath(name).parent.name, 'description': front['description']}, sort_keys=False).strip()
    return f'---\n{header}\n---\n\n{body}'.encode()


def adapt(data, name, adaptations, warnings=None):
    """Apply unambiguous known translations; source wins when wording changes."""
    warnings = warnings if warnings is not None else []
    entry = adaptations.get(name, {})
    replacements = []
    active = set()
    for index, rule in enumerate(entry.get('rules', [])):
        matches = [v for v in rule['variants'] if v['upstream'].encode() in data]
        if len(matches) != 1 or not matches[0]['upstream'] or data.count(matches[0]['upstream'].encode()) != 1:
            warnings.append(f'{name}: translation {index + 1} missing or ambiguous; upstream retained')
            continue
        source = matches[0]['upstream'].encode()
        start = data.index(source)
        replacements.append((start, start + len(source), matches[0]['codex'].encode(), index))
    # Never apply either side of overlapping rules.
    overlaps = {i for i, a in enumerate(replacements) for j, b in enumerate(replacements)
                if i != j and a[0] < b[1] and b[0] < a[1]}
    if overlaps:
        warnings.append(f'{name}: overlapping translations; upstream retained for affected fragments')
    end, rendered = 0, []
    for start, stop, replacement, index in sorted(r for i, r in enumerate(replacements) if i not in overlaps):
        rendered.extend((data[end:start], replacement))
        active.add(index)
        end = stop
    rendered.append(data[end:])
    data = b''.join(rendered)
    for replacement in entry.get('substitutions', []):
        source = replacement['upstream'].encode()
        if source and source in data:
            data = data.replace(source, replacement['codex'].encode())
        else:
            warnings.append(f'{name}: substitution missing; upstream retained')
    if SKILL_PATH.fullmatch(name):
        data = normalize_skill(data, name)
    if name.startswith('agents/') and name.endswith('.md'):
        data = b'Read ../CODEX-RUNTIME.md before applying these role instructions.\n\n' + data
    return data, active


def inventory(root):
    result = {}
    if root.is_symlink():
        raise SyncConflict(f'Cannot use symlink: {root}')
    for path in root.rglob('*'):
        if path.is_symlink():
            raise SyncConflict(f'Cannot use symlink: {path}')
        if path.is_file():
            result[path.relative_to(root).as_posix()] = (path.read_bytes(), path.stat().st_mode & 0o777)
    return result


def sync(root, upstream, ref, validator=validate, report=None):
    root, upstream = Path(root).resolve(), Path(upstream).resolve()
    report = report if report is not None else {}
    warnings = []
    state_path = root / 'upstream.json'
    state = json.loads(state_path.read_text())
    try:
        head = git(upstream, 'rev-parse', f'{ref}^{{commit}}').decode().strip()
    except subprocess.CalledProcessError as error:
        raise SyncConflict('Upstream ref is missing or inaccessible') from error
    source = snapshot(upstream, head)
    if not any(SKILL_PATH.fullmatch(name) and not preserved(name) for name in source):
        raise SyncConflict('Upstream package has no skills; refusing an empty replacement')
    try:
        version = json.loads(source['.cursor-plugin/plugin.json'][0])['version']
        if not isinstance(version, str) or not re.fullmatch(r'\d+\.\d+\.\d+', version):
            raise ValueError('expected major.minor.patch')
    except (ValueError, KeyError, TypeError) as error:
        raise SyncConflict('Missing or invalid upstream pstack version') from error
    plugin = root / 'plugins/pstack-for-codex'
    if (root / 'plugins').is_symlink() or state_path.is_symlink():
        raise SyncConflict('Cannot write through a package/state symlink')
    current = inventory(plugin)
    desired = {n: v for n, v in current.items() if preserved(n)}
    adaptations = json.loads(ADAPTATIONS_PATH.read_text())
    targets = set()
    for name, (data, mode) in source.items():
        if preserved(name):
            continue
        target = target_path(name)
        if target in targets:
            raise SyncConflict(f'Upstream destination collision: {target}')
        targets.add(target)
        if target.startswith('references-host/'):
            desired[target] = (data, mode)
        else:
            desired[target] = (adapt(data, name, adaptations, warnings=warnings)[0], mode)
    # Metadata is generated/owned by Codex, not inherited from another host.
    for name in list(desired):
        if not SKILL_PATH.fullmatch(name) or preserved(name):
            continue
        skill_name = PurePosixPath(name).parent.name
        meta = str(PurePosixPath(name).parent / 'agents/openai.yaml')
        desired[meta] = current.get(meta, (yaml.safe_dump({
            'interface': {'display_name': skill_name.replace('-', ' ').title(),
                          'short_description': 'Engineering workflow for Codex',
                          'default_prompt': f'Use ${skill_name} for this task.'},
            'policy': {'allow_implicit_invocation': False}}, sort_keys=False).encode(), 0o644))
    manifest = json.loads(current['plugin.json'][0])
    manifest['version'] = version
    desired['plugin.json'] = ((json.dumps(manifest, indent=2) + '\n').encode(), 0o644)
    state['commit'] = head
    state_bytes = (json.dumps(state, indent=2) + '\n').encode()
    report.update(source_commit=head, version=version,
                  added=len(desired.keys() - current.keys()),
                  deleted=len(current.keys() - desired.keys()),
                  modified=sum(desired[n] != current[n] for n in desired.keys() & current.keys()))
    # Stage only the package and its schema/marketplace dependencies. Do not copy
    # a caller's unrelated working files, credentials or Git metadata.
    with tempfile.TemporaryDirectory(dir=root.parent, prefix='.sync-candidate-') as tmp:
        staged = Path(tmp)
        for name in ['schemas', '.agents']:
            if (root / name).exists():
                shutil.copytree(root / name, staged / name)
        candidate = staged / 'plugins/pstack-for-codex'
        candidate.mkdir(parents=True)
        for name, (data, mode) in desired.items():
            path = candidate / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            path.chmod(mode)
        (staged / 'upstream.json').write_bytes(state_bytes)
        if validator is not None:
            try:
                if validator is validate:
                    validate(staged, warnings=warnings)
                else:
                    validator(staged)
            except Exception as error:
                raise SyncConflict(f'Proposed package failed validation: {error}') from error
        changed = desired != current or state_bytes != state_path.read_bytes()
        if changed:
            backup = staged / 'previous-plugin'
            previous_state = state_path.read_bytes()
            plugin.rename(backup)
            try:
                candidate.rename(plugin)
                replacement = staged / 'upstream.json'
                os.replace(replacement, state_path)
            except Exception:
                if plugin.exists():
                    shutil.rmtree(plugin)
                backup.rename(plugin)
                state_path.write_bytes(previous_state)
                raise
    report.update(status='UPDATED' if changed else 'UNCHANGED', warnings=sorted(set(warnings)))
    return changed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--upstream-dir', type=Path, required=True)
    parser.add_argument('--ref', default='HEAD')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    report = {}
    try:
        sync(args.repo, args.upstream_dir, args.ref, report=report)
    except Exception as error:
        report.update(status='ERROR', error=str(error))
        raise
    finally:
        if args.report:
            args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(report['status'])
    print(f"Source {report['source_commit']}: +{report['added']} ~{report['modified']} -{report['deleted']}")
    for warning in report['warnings']:
        print(f'WARNING: {warning}')


if __name__ == '__main__':
    main()
