#!/usr/bin/env python3
"""Mirror explicitly selected immutable images, including same-version rebuilds."""

import json
import os
from pathlib import Path
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor


def transfer(arguments, timeout):
    for attempt in range(5):
        try:
            return subprocess.run(['docker', *arguments], check=True, timeout=timeout)
        except subprocess.CalledProcessError:
            if attempt == 4:
                raise
            time.sleep(5 * 2 ** attempt)


def main():
    images = json.loads(os.environ['MIRROR_IMAGES'])
    if not isinstance(images, list) or not 1 <= len(images) <= 20:
        raise ValueError('Expected between 1 and 20 image specifications')
    # Validate the entire request before publishing any image.
    for item in images:
        if set(item) != {'source', 'name', 'tag'}:
            raise ValueError('Each image requires source, name and tag')
        if not re.fullmatch(r'[A-Za-z0-9./:_-]+@sha256:[0-9a-f]{64}', item['source']):
            raise ValueError('Source must be an immutable image reference')
        if not re.fullmatch(r'[a-z0-9]+(?:[._-][a-z0-9]+)*', item['name']):
            raise ValueError('Invalid target repository name')
        if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}', item['tag']):
            raise ValueError('Invalid target tag')

    prefix = f"{os.environ['MIRROR_REGISTRY']}/{os.environ['MIRROR_NAMESPACE']}"
    def mirror(item):
        target = f"{prefix}/{item['name']}:{item['tag']}"
        transfer(['pull', '--platform', 'linux/amd64', item['source']], timeout=600)
        subprocess.run(['docker', 'tag', item['source'], target], check=True)
        # Publish the platform that was pulled, rather than an incomplete
        # upstream multi-platform index retained by containerd image stores.
        transfer(['push', '--platform', 'linux/amd64', target], timeout=1200)
        result = subprocess.run(
            ['docker', 'image', 'inspect', '--format', '{{json .RepoDigests}}', target],
            capture_output=True, text=True, check=True,
        )
        with Path(os.environ['GITHUB_STEP_SUMMARY']).open('a') as summary:
            summary.write(f"- `{target}` from `{item['source']}`\n  Digests: `{result.stdout.strip()}`\n")
        subprocess.run(['docker', 'image', 'rm', target, item['source']], check=True)

    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(mirror, images))


if __name__ == '__main__':
    main()
