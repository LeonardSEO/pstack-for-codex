import json
import re
import sys
from pathlib import Path

import jsonschema
import yaml


def validate(root):
    root = Path(root)
    plugin = root / 'plugins/pstack-for-codex'
    manifest = json.loads((plugin / 'plugin.json').read_text())
    schema = json.loads((root / 'schemas/plugin.schema.json').read_text())
    jsonschema.validate(manifest, schema)
    assert manifest['name'] == plugin.name
    assert re.fullmatch(r'\d+\.\d+\.\d+', manifest['version'])
    ui = manifest['extensions']['com.openai']['interface']
    assert len(ui['shortDescription']) <= 30
    for field in ['logo', 'composerIcon']:
        assert ui[field].startswith('./')
        asset = (plugin / ui[field]).resolve()
        assert asset.is_relative_to(plugin.resolve()) and asset.is_file()
    marketplace = json.loads((root / '.agents/plugins/marketplace.json').read_text())
    assert marketplace['name'] == 'leonardseo-pstack'
    entry = marketplace['plugins'][0]
    assert entry['name'] == manifest['name']
    assert entry['source'] == {'source': 'local', 'path': './plugins/pstack-for-codex'}
    skills = list((plugin / 'skills').glob('*/SKILL.md'))
    assert skills
    assert (plugin / 'skills/thermo-nuclear-code-quality-review/SKILL.md').is_file(), 'Required independent review skill is missing'
    assert 'Copyright (c) 2026 Cursor' in (plugin / 'LICENSE-cursor-team-kit').read_text()
    for path in skills:
        front = yaml.safe_load(path.read_text().split('---', 2)[1])
        assert set(front) == {'name', 'description'}, path
        assert front['name'] == path.parent.name, path
        assert re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', front['name']), path
        assert isinstance(front['description'], str) and front['description'], path
        assert 'CODEX-RUNTIME.md' in path.read_text(), path
        metadata = yaml.safe_load((path.parent / 'agents/openai.yaml').read_text())
        assert metadata['policy']['allow_implicit_invocation'] is False, path
    instructional_files = list((plugin / 'skills').rglob('*.md')) + list((plugin / 'agents').rglob('*.md'))
    for path in instructional_files:
        text = path.read_text()
        for forbidden in ['subagent_type:', 'run_in_background:', 'cloud_base_branch', '~/.cursor/', 'AskQuestion', '/loop', 'update_state', 'SendToUser']:
            assert forbidden not in text, f'{path}: unsupported {forbidden}'
        assert not re.search(r'\b(?:claude-opus|grok)-\d', text), path
        assert not re.search(r'^(?:<{7}|\|{7}|={7}|>{7})(?:\s|$)', text, re.M), path
        for match in re.finditer(r'\[[^\]]*\]\(([^)]+)\)', text):
            target = match.group(1).split('#')[0]
            if not target or target == 'url' or re.match(r'\w+:', target) or '<' in target:
                continue
            resolved = (path.parent / target).resolve()
            assert resolved.is_relative_to(plugin.resolve()) and resolved.exists(), f'{path}: broken {target}'
    for path in plugin.rglob('*'):
        assert not path.is_symlink(), path
        assert path.name not in ['node_modules', '__pycache__', '.git'], path
    return len(skills)


if __name__ == '__main__':
    try:
        print(f'PASS: {validate(Path(__file__).resolve().parents[1])} skills, manifest, marketplace, links and Codex compatibility')
    except (AssertionError, ValueError, KeyError, OSError, jsonschema.ValidationError, yaml.YAMLError) as error:
        print(f'Validation failed: {error}', file=sys.stderr)
        sys.exit(1)
