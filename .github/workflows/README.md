# Workflow System Documentation

This directory contains a flexible, modular workflow system for syncing container images from various sources to your private registry.

## Architecture Overview

The system consists of three main components:

### 1. Composite Actions (`sync-setup`)

**Location**: `.github/actions/sync-setup/`

Reusable setup action that handles common initialization:
- Python environment setup
- Python dependencies installation
- Docker registry login
- GitHub CLI installation

### 2. Workflow Templates

#### Multi-Component Template (`sync-multi-template.yml`)
For complex scenarios with multiple components.

### 3. Sync Scripts

#### `sync_multi.py` - Multi-component orchestrator

## Quick Start Examples

### Multi-Component Sync
```yaml
jobs:
  sync:
    uses: ./.github/workflows/sync-multi-template.yml
    with:
      config: |
        {
          "version_key": "apache/guacamole",
          "source_repo": "apache/guacamole-server",
          "sync_type": "tag",
          "components": [
            {"type": "image", "images": ["guacamole/guacamole"]},
            {"type": "dockerfile", "image_name": "guacd", "dockerfile": "..."}
          ]
        }
    secrets: inherit
```

See individual workflow files for more examples.

## Security maintenance images

`sync-pinned-images.yml` publishes the immutable source references in
`.github/pinned-images.json` when that manifest or its helper changes. It also
accepts an `images` JSON input on manual dispatch. The helper validates the
whole batch before publishing amd64 images and retries transient registry
failures. Use this for vendor rebuilds that retain an application version tag.

`sync-nextcloud.yml` tracks the stable Nextcloud 35 Apache images. Its version
record is `nextcloud/apache-stable`; the obsolete release-candidate tracker was
removed.

`build-immich-postgres.yml` builds the PG14 database security image. Its pinned
base contains the PostgreSQL and OS package refresh, and the Dockerfile applies
current package updates and pgvector fixes. Build guards require PostgreSQL
14.24 or later in major 14 and pgvector 0.8.7 or later. The VectorChord extension
stays at 0.4.3. The homelab deployment pins the published image digest.
