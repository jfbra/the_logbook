# CI builds images to GHCR; deploys are a manual push over Tailscale

CI runs on GitHub-hosted runners and the image is built once there and pushed to GitHub's container registry (a public package, tagged `sha-<short>`), so the image that runs in production is the one CI tested. Deploying is a manual "Run workflow" click in a `production` Environment limited to `master`: the job joins the tailnet as a temporary, tagged node (OIDC federation, with an OAuth client as the fallback), reaches the VM over Tailscale SSH, and runs `docker compose pull && docker compose up -d` for the chosen commit. Rolling back is the same click with an older commit. We chose push over pull because it makes "deploy only what CI passed" structural and auditable while the VM keeps no inbound exposure.

## Considered options

- **Self-hosted runner on the VM:** rejected. GitHub advises against self-hosted runners on public repositories, and a job would run on the machine that holds the data.
- **Watchtower or a polling timer on the VM:** rejected. Watchtower is archived and unmaintained, and a poller cannot enforce that CI passed unless it is scripted to check.
- **Building on the VM (the manual flow today):** kept until the deploy stage exists. The deployed image is then not the one CI tested.
- **Automatic deploy on every merge, or auto-rollback on a failed health check:** deferred. A failed health check fails the job loudly instead, because rolling code back after a migration has applied can fail in a different way.

## Consequences

- The tailnet's default allow-all access rule has to be replaced with explicit rules (the owner's devices keep full access, `tag:ci` reaches only the VM's SSH port, and the VM is tagged), otherwise a tagged CI node can reach every device. This is a tailnet-wide change that can lock the owner out if done in the wrong order, so the new rules go in beside the allow-all rule, are tested, and only then replace it.
- Migrations stay on container start. To keep a one-version rollback safe, every migration must stay backwards-compatible for one release.
- Automated deploy is gated on database backups existing, and backups are not set up yet, so only CI (and the merge gate) is built first.
