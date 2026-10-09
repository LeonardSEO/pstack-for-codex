#!/usr/bin/env bash
set -euo pipefail

version=$(python3 -c 'import json; print(json.load(open("plugins/pstack-for-codex/plugin.json"))["version"])')
tag="v$version"
if draft=$(gh release view "$tag" --json isDraft --jq '.isDraft'); then
  if [[ "$draft" == false ]]; then
    echo "Release $tag already published."
    exit 0
  fi
  commit=$(gh release view "$tag" --json targetCommitish --jq '.targetCommitish')
  git fetch origin "$commit"
else
  commit=$(git rev-parse HEAD)
  upstream=$(python3 -c 'import json; print(json.load(open("upstream.json"))["commit"])')
  gh release create "$tag" --target "$commit" --draft \
    --title "pstack for Codex $version" --generate-notes \
    --notes "Validated plugin snapshot. Pinned pstack upstream: https://github.com/cursor/plugins/commit/$upstream"
fi

package_dir=$(mktemp -d)
trap 'rm -rf "$package_dir"' EXIT
archive="pstack-for-codex-$version.zip"
git archive --format=zip --prefix="pstack-for-codex-$version/" \
  --output="$package_dir/$archive" "$commit"
(cd "$package_dir" && shasum -a 256 "$archive" > SHA256SUMS)
gh release upload "$tag" "$package_dir/$archive" "$package_dir/SHA256SUMS" --clobber
gh release edit "$tag" --draft=false --latest
