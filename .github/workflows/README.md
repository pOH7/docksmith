# Workflow System Documentation

This directory contains a flexible, modular workflow system for syncing container images from various sources to your private registry.

## Architecture Overview

The system consists of three main components:

### 1. Composite Actions (`sync-setup`)

**Location**: `.github/actions/sync-setup/`

Reusable setup action that handles common initialization:
- Python environment setup
- Python dependencies installation
- Docker Buildx setup
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
