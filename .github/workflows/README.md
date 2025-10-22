# GitHub Actions Release Sync Workflows

This directory contains automated workflows that sync GitHub releases to your homelab infrastructure. The system automatically detects new releases, builds/syncs Docker images, uploads artifacts to MinIO, and creates pull requests with version updates.

## Architecture

### Per-Project Template Approach

The system uses a **reusable workflow template** pattern where:
- One shared template (`sync-template.yml`) contains all the common logic
- 26 individual workflow files (one per project) call the template with project-specific parameters
- Each workflow can have its own schedule and can be independently enabled/disabled

### Benefits

- **Independent execution**: Each project runs on its own schedule
- **Failure isolation**: One project failure doesn't block others
- **Custom schedules**: High-frequency projects check more often
- **Easy maintenance**: Fix the template once, all projects benefit
- **Clear monitoring**: GitHub UI shows status per project
- **No git conflicts**: Each workflow creates its own PR

## File Structure

```
.github/
├── workflows/
│   ├── sync-template.yml                    # Reusable workflow template
│   ├── sync-minio.yml                       # Individual project workflows (26 total)
│   ├── sync-openvscode-server.yml
│   ├── sync-sillytavern.yml
│   └── ...
└── scripts/                                 # Python modules
    ├── requirements.txt                     # Python dependencies
    ├── sync_project.py                      # Main orchestrator (3 sync actions)
    ├── github_api.py                        # GitHub API operations
    ├── dockerhub_api.py                     # DockerHub API operations
    ├── docker_operations.py                 # Docker build/pull/push
    ├── minio_operations.py                  # MinIO artifact uploads
    ├── version_manager.py                   # Version file management
    └── pr_manager.py                        # PR creation/auto-merge
```

## Workflow Schedules

Projects are scheduled based on their typical update frequency. All times are set to run at 2 AM UTC+8 (18:00 UTC):

### High Frequency (Every 6 hours)
Runs at 2AM, 8AM, 2PM, 8PM UTC+8:
- MinIO
- OpenVSCode Server
- Immich
- Jellyfin

### Daily (2 AM UTC+8 / 18:00 UTC)
- SillyTavern
- Guacamole Server
- Vaultwarden
- v2rayA
- Metatube Server
- qBittorrent ClientBlocker
- AdGuard Home
- Photoprism
- qBittorrent
- All LinuxServer projects (Radarr, Sonarr, Prowlarr, Bazarr, Plex, Lidarr, WireGuard, Calibre-Web, Resilio Sync)

### Every 3 Days (2 AM UTC+8 / 18:00 UTC)
- Anki
- Cert Manager
- Istio

### Weekly (Sunday 2 AM UTC+8 / 18:00 UTC)
- PlantUML Server

All workflows can also be triggered manually via `workflow_dispatch`.

## How It Works

### 1. Version Detection
- Each workflow checks GitHub API for the latest release/tag
- Applies version transformations if configured (`remove_v_prefix`, `split_dash_first`, etc.)
- Compares with stored version in `release-versions/*.txt`
- Proceeds only if version has changed

### 2. Sync Operation
Each workflow specifies a `sync_action` parameter:

#### **pull_tag_push** (Simple Image Sync)
- Pulls source image from registry
- Re-tags for Alibaba Cloud registry
- Pushes to `registry.cn-hangzhou.aliyuncs.com/pohvii`
- Example: MinIO, Vaultwarden, SillyTavern

#### **build_and_push** (Custom Docker Build)
- Builds Docker image from inline Dockerfile
- Replaces `{VERSION}` placeholder with actual version
- Pushes to Alibaba Cloud registry
- Example: Guacamole, Jellyfin, qBittorrent, AdGuard Home

#### **pull_tag_push_multiple** (Multiple Images)
- Syncs multiple related images with same version
- Pulls, tags, and pushes each image
- Example: Cert-Manager (5 images), Istio (2 images), Immich (2 images)

### 3. PR Creation
- Updates version file in `release-versions/`
- Creates a new branch
- Commits the change
- Creates pull request
- Enables auto-merge (squash merge)

### 4. Auto-Merge
- PR auto-merges when all checks pass
- No manual intervention required
- Version tracking stays in sync

## Setup Requirements

### Repository Secrets

Configure these secrets in GitHub repository settings:

| Secret | Description |
|--------|-------------|
| `MINIO_URL` | MinIO server URL (e.g., `https://minio.example.com`) |
| `MINIO_ACCESS_KEY` | MinIO access key |
| `MINIO_SECRET_KEY` | MinIO secret key |
| `DOCKER_REGISTRY` | Docker registry URL (e.g., `registry.cn-hangzhou.aliyuncs.com`) |
| `DOCKER_REGISTRY_USER` | Docker registry username |
| `DOCKER_REGISTRY_PASSWORD` | Docker registry password |
| `DOCKER_REGISTRY_NAMESPACE` | Registry namespace for images (e.g., `pohvii`) |

The `GITHUB_TOKEN` is automatically provided by GitHub Actions.

### Repository Settings

1. **Enable auto-merge**:
   - Settings → General → Allow auto-merge ✓

2. **Workflow permissions**:
   - Settings → Actions → General → Workflow permissions
   - Select "Read and write permissions" ✓

## Adding a New Project

To add a new project to sync, create a workflow file with the appropriate sync action:

### Example 1: Simple Pull/Tag/Push

Create `.github/workflows/sync-myproject.yml`:

```yaml
name: Sync My Project

on:
  schedule:
    - cron: '0 18 * * *'  # Daily at 2 AM UTC+8
  workflow_dispatch:

jobs:
  sync:
    uses: ./.github/workflows/sync-template.yml
    with:
      repo: 'owner/repo'
      sync_type: 'release'
      sync_action: 'pull_tag_push'
      source_images: |
        - source/image-name
    secrets: inherit
```

### Example 2: Custom Docker Build

```yaml
jobs:
  sync:
    uses: ./.github/workflows/sync-template.yml
    with:
      repo: 'owner/repo'
      sync_type: 'release'
      sync_action: 'build_and_push'
      target_image: 'my-custom-image'
      dockerfile: |
        FROM base-image:{VERSION}
        RUN apt-get update && apt-get install -y my-package
    secrets: inherit
```

### Example 3: Multiple Images

```yaml
jobs:
  sync:
    uses: ./.github/workflows/sync-template.yml
    with:
      repo: 'owner/repo'
      sync_type: 'release'
      sync_action: 'pull_tag_push_multiple'
      source_images: |
        - source/image-1
        - source/image-2
        - source/image-3
    secrets: inherit
```

### Example 4: With Version Transform

```yaml
jobs:
  sync:
    uses: ./.github/workflows/sync-template.yml
    with:
      repo: 'owner/repo'
      sync_type: 'release'
      sync_action: 'pull_tag_push'
      source_images: |
        - source/image
      version_transform: |
        - remove_v_prefix
        - skip_rc_beta
    secrets: inherit
```

### Test Your Workflow

1. Go to Actions tab in GitHub
2. Select your new workflow
3. Click "Run workflow"

## Monitoring

### View Workflow Status
- GitHub → Actions tab
- Each project shows as a separate workflow
- Green check = successful sync
- Red X = failed sync

### View PRs
- All version update PRs are automatically created
- Tagged with project name in title
- Auto-merge enabled if checks pass

### Logs
- Click on any workflow run to see detailed logs
- Python scripts output structured logging
- Docker operations are logged

## Troubleshooting

### Workflow Fails to Create PR
**Cause**: Missing permissions or auto-merge not enabled
**Solution**: Check repository settings for workflow permissions and auto-merge

### Docker Build Fails
**Cause**: Base image changed or build dependencies unavailable
**Solution**: Check workflow `dockerfile` parameter, may need to update inline Dockerfile

### MinIO Upload Fails
**Cause**: Invalid credentials or network issue
**Solution**: Verify MINIO_URL, MINIO_ACCESS_KEY, MINIO_SECRET_KEY secrets

### No Version Change Detected
**Cause**: Version file already updated or API rate limit
**Solution**: Check `release-versions/*.txt` file, verify GitHub token has access

### Auto-Merge Not Working
**Cause**: Branch protection rules or checks required
**Solution**: Configure branch protection to allow auto-merge or ensure all checks pass

## Disabled Projects

The following projects from the original `build.sh` are currently disabled (commented out):
- ArchiveBox
- yanwk/comfyui-boot
- nextcloud/server
- jgm/pandoc
- pqrs-org/Karabiner-Elements
- dbeaver/dbeaver
- adoptium/temurin17-binaries
- adoptium/temurin8-binaries
- Bin-Huang/chatbox
- Node.js releases
- yuzutech/kroki
- alibaba/arthas

To enable any of these, create a workflow file and add the sync strategy following the "Adding a New Project" guide above.

## Migration from build.sh

This GitHub Actions system replaces the original `build.sh` script. Key improvements:

| Feature | build.sh | GitHub Actions |
|---------|----------|----------------|
| **Execution** | Manual/cron on server | Automated in GitHub cloud |
| **Parallelization** | Sequential | Independent per-project |
| **Monitoring** | Log files | GitHub UI with status badges |
| **Failure handling** | Stops on error | Isolated failures |
| **Scheduling** | Single schedule | Custom per project |
| **Dependencies** | Bash, jq, docker, mc | Python, managed in cloud |
| **PR Creation** | Manual git commands | Automated with auto-merge |

The original `build.sh` can be kept for reference or local testing.

## Workflow Parameters Reference

### Sync Actions

| Action | Description | Required Parameters |
|--------|-------------|---------------------|
| `pull_tag_push` | Simple image pull/tag/push | `source_images` (list with 1 item) |
| `build_and_push` | Build custom Docker image | `dockerfile`, `target_image` |
| `pull_tag_push_multiple` | Sync multiple images | `source_images` (list with multiple items) |

### Version Transformations

| Transform | Effect | Example |
|-----------|--------|---------|
| `none` | Use version as-is | v1.2.3 → v1.2.3 |
| `remove_v_prefix` | Remove leading 'v' | v1.2.3 → 1.2.3 |
| `split_dash_first` | Take first part before dash | 250101-abc123 → 250101 |
| `skip_rc_beta` | Skip rc/beta versions | v1.0.0-rc1 → (skipped) |

Transformations are applied in order. Multiple transforms can be combined.
