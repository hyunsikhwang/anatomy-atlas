# Anatomy Atlas project instructions

## Source control

- Manage all future changes in `https://github.com/hyunsikhwang/anatomy-atlas.git`, using the `github` remote and `main` branch.
- Commit code, 3D model assets, provenance, and supporting scripts together. Verify the remote commit after every synchronization. Use the connected GitHub API if shell Git authentication is unavailable.
- The current application source and all four v13 model segments are imported into GitHub. Use GitHub main as the starting point for subsequent changes. Verify the complete tree and model checksums when migrating or synchronizing.
- Preserve the existing source and history in the Sites source repository and local `sites-before-github` branch. The live revision 13 source commit is `61c7151b2deb3e7ff92ccb093157815041574e48`.
- Keep the `sites` remote separate for publication. Preserve both repositories' history and do not force-push. GitHub is the required destination for future source changes; a Sites push or local commit alone is not GitHub synchronization.
- Exclude uploaded user attachments, credentials, dependencies, build output, and scratch caches.
- If synchronization fails or is interrupted, preserve completed work and explicitly report the incomplete upload.

## Existing publication

- Preserve the Sites project ID in `.openai/hosting.json` and the existing URL `https://anatomy-atlas.wonderful-writing.chatgpt.site`.
