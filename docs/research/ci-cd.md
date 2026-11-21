# CI/CD options for The Logbook

Date: 2026-11-22

Method: every claim below was read from a primary source during this session (official GitHub, Tailscale, Docker, Astral, Django and PostgreSQL docs; action repos' READMEs; the GitHub REST API for release tags). The fetch tool summarises pages, so quotes are as returned by it; where it could not quote something, that is listed under "Unverified". Action versions are "latest release as of 2026-11-22" from `https://api.github.com/repos/<owner>/<repo>/releases/latest`.

## Summary

GitHub-hosted runners are free for public repos and already carry Python 3.14 (as a cached tool), so a CI job using `astral-sh/setup-uv`, `uv sync --locked` and a `postgres` service container with a `pg_isready` health check is straightforward. To make CI gate merges, a ruleset (or the classic rule) can require a status check; a solo owner can merge their own PR as long as required approvals is 0 (authors cannot approve their own PRs), and a workflow filtered with `paths:` that does not run leaves the required check Pending and blocks the merge. For deploying to a Tailscale-only VM, three designs exist: (a) a GitHub-hosted runner joins the tailnet as an ephemeral tagged node (via `tailscale/github-action@v4`, OIDC workload identity federation is the documented "recommended" method) and SSHes in, needing no inbound exposure of the VM; (b) a self-hosted runner on the VM (GitHub itself recommends against this for public repos); (c) pull-based updates from the VM (no inbound, no Tailscale credentials in GitHub; Watchtower is archived). Building images in Actions and pushing to ghcr.io is free and supports sha-tagged rollback, but adds registry auth on the VM; building on the VM is simplest. Migrations-on-start with an automated deploy needs a pre-deploy `pg_dump` and backwards-compatible migrations discipline.

---

## 1. GitHub Actions CI: uv + Python 3.14 + Postgres service

### Python 3.14 availability
- The `actions/python-versions` manifest (the source `setup-python` downloads from) lists 3.14.10, 3.14.9 ... 3.14.2 (and rc builds). Seen at https://raw.githubusercontent.com/actions/python-versions/main/versions-manifest.json
- The Ubuntu 24.04 runner image README lists Python 3.12.3 as the system Python and Python 3.14.10 under "Cached Tools"; Postgres 16.16 is installed but disabled by default; Docker 28.0.4. Seen at https://raw.githubusercontent.com/actions/runner-images/main/images/ubuntu/Ubuntu2404-Readme.md
- So 3.14 is available on GitHub-hosted runners, either via the cached tool / `actions/setup-python` or by uv downloading it.
- Postgres on the runner is v16, not 17: use a `postgres:17` service container to match production (the image name/tag is my choice; the docs example uses `image: postgres`).

### Current action versions
| Action | Latest release (GitHub API) | Version shown in docs |
|---|---|---|
| `astral-sh/setup-uv` | v10.4.0 (2026-11-20) | README shows `@1db35dd8... # v10.4.0`; uv docs page shows `@c771a70e... # v9.0.0` (docs page is behind) |
| `actions/checkout` | v7.0.1 | uv docs: `3d3c42e5... # v7.0.1` |
| `actions/setup-python` | v7.1.0 | README: `actions/setup-python@v7` |
| `actions/cache` | v6.1.0 | uv docs: `55cc8345... # v6.1.0` |

Sources: https://api.github.com/repos/astral-sh/setup-uv/releases/latest (and the other three repos at the same path); https://github.com/astral-sh/setup-uv; https://docs.astral.sh/uv/guides/integration/github/; https://github.com/actions/setup-python

### Recommended pattern per the docs
- uv's official GitHub integration guide: install with `astral-sh/setup-uv` (optionally `with: version: "0.13.9"`), install Python with `run: uv python install`, cache with `enable-cache: true` on setup-uv, and sync with `uv sync --locked --all-extras --dev`. The guide uses SHA-pinned references with version comments. https://docs.astral.sh/uv/guides/integration/github/
- setup-uv inputs (README): `python-version` ("set the environment variable `UV_PYTHON` for the rest of your workflow"), `enable-cache` (`true`, `false`, or `auto`), `cache-dependency-glob`, `activate-environment`. "By default, this action installs the latest version of uv." https://github.com/astral-sh/setup-uv
- The uv docs show `uv cache prune --ci` as a step to minimise the cache when using manual `actions/cache` with `UV_CACHE_DIR`. https://docs.astral.sh/uv/guides/integration/github/
- `--locked` vs `--frozen`: `--locked` errors if the lockfile is out of date ("If the lockfile is not up-to-date, uv will raise an error instead of updating the lockfile."); `--frozen` uses the lockfile without checking ("To use the lockfile without checking if it is up-to-date, use the `--frozen` option."). The page documents these under `uv run`, not `uv sync` specifically. https://docs.astral.sh/uv/concepts/projects/sync/ The official CI guide uses `--locked`; `--frozen` is not shown in it. For CI, `--locked` additionally catches a `pyproject.toml`/`uv.lock` mismatch.
- The `dev` dependency group "is special-cased and synced by default" (same sync page), so `uv sync --locked` already installs ruff/pyright/pytest if they are in `[dependency-groups] dev`.
- `actions/setup-python` is an alternative: `uses: actions/setup-python@v7` with `python-version: '3.13'` and `cache: 'pip'` shown in README (the README does not mention 3.14 explicitly). For a uv project, the uv guide uses uv itself to install Python, so setup-python is not needed.

### Postgres service container (GitHub docs)
Documented pattern (https://docs.github.com/en/actions/tutorials/use-containerized-services/create-postgresql-service-containers):
```yaml
services:
  postgres:
    image: postgres
    env:
      POSTGRES_PASSWORD: postgres
    options: >-
      --health-cmd pg_isready
      --health-interval 10s
      --health-timeout 5s
      --health-retries 5
    ports:
      - 5432:5432
```
- Job running directly on the runner: "You can access service containers from the Docker host using `localhost` and the Docker host port number" (docs set `POSTGRES_HOST` to `localhost`). Job running in a container: use the service label (`postgres`) as host. Same page.
- Fit for this repo: the app reads `POSTGRES_HOST/PORT/DB/USER/PASSWORD`; set `POSTGRES_USER`, `POSTGRES_DB`, `POSTGRES_PASSWORD` to `logbook` on the service and `ports: - 5432:5432`. The docs example only sets `POSTGRES_PASSWORD`; extra env vars are standard postgres image behaviour but I did not fetch the Docker Hub page to cite them (see Unverified). The health check `pg_isready` may need `-U logbook` in some setups; not verified.

### Steps for the checks
No official doc prescribes the ruff/pyright/pytest commands; these are the project's own tools. Sketch (not from a source; adapt):
```yaml
permissions:
  contents: read
steps:
  - uses: actions/checkout@<sha> # v7.0.1
  - uses: astral-sh/setup-uv@<sha> # v10.4.0
    with: { enable-cache: true, python-version: "3.14" }
  - run: uv sync --locked
  - run: uv run ruff check .
  - run: uv run ruff format --check .
  - run: uv run pyright
  - run: uv run pytest
```

---

## 2. Required checks on `master`: branch protection vs rulesets

### Required status checks
- Required checks must be "successful", "skipped", or "neutral" to merge. Strict mode requires the branch be up to date with base. Job names should be unique across workflows: "Using the same job name in multiple workflows can cause ambiguous status check results". https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
- Checks are matched by name (rulesets: "enter each check's name and click the plus button"); with "Require branches to be up to date" you must define a check for it to take effect. https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository In rulesets "you can select an app as the expected source of status updates." https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets
- Whether the matched name is the job `name:` or `workflow / job` was not stated in the pages I read (see Unverified).

### Path-filter pitfall (verified)
- Skipped by path, branch or commit-message filtering: "Associated checks stay in a 'Pending' state and block merging." Advice: avoid requiring workflows that can be skipped. A job skipped by a conditional (`if:`) reports "Success" and does not block. https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories-with-code-quality-features/troubleshooting-required-status-checks
- Implication: do not put `paths:`/`paths-ignore:` on the CI workflow's `pull_request` trigger. If path filtering is wanted, run the workflow always and gate inside via job `if:`.

### Classic branch protection vs rulesets
- Only one branch protection rule applies at a time; "Multiple rulesets can apply to the same branch at the same time"; rulesets can be toggled on/off without deleting; anyone with read access can view active rulesets; rules from overlapping rulesets combine with the most restrictive winning ("A ruleset does not have a priority"). https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets and the protected-branches page above.
- Rulesets: bypass list actors can be repo admins, maintain/write roles, teams, GitHub Apps, Dependabot. Bypass modes: "Always allow" (default) and "For pull requests only" (the actor must open a PR then can bypass protections and merge it, leaving an audit trail). Enforcement: Active, Disabled, Evaluate. https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository
- Ruleset rules: "Required approvals can be set from 0 (zero) to 10"; "Require branches to be up to date before merging"; block force pushes ("enabled by default"); restrict deletions ("only users with bypass permissions can delete"). https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets
- Classic rule: by default restrictions do not apply to admins; the "Do not allow bypassing the above settings" option applies them to admins too. Same protected-branches page.

### Solo owner merging own PRs
- "Pull request authors cannot approve their own pull requests." https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/approving-a-pull-request-with-required-reviews
- Hence for a solo developer: require a PR with 0 required approvals (documented range 0-10 in rulesets) plus the required status check; a 1-approval requirement would need an admin bypass. Using a bypass list with "For pull requests only" keeps the PR flow but lets the owner merge when CI is red/stuck, with an audit trail.
- Rulesets are documented as limited to Team/Enterprise for *organization* rulesets; the page sets no plan requirement for repository rulesets (only that organization-level ones need Team/Enterprise). The about-rulesets page says rulesets "are available for customers on GitHub Team and GitHub Enterprise plans" (see Unverified: public-repo-on-Free availability not confirmed; the owner's own settings page offered conversion, which is circumstantial evidence only).

---

## 3. Deploying to a Tailscale-only VM

### (a) `tailscale/github-action` on a GitHub-hosted runner
- Latest release v4.4.0 (2026-10-29); usage `uses: tailscale/github-action@v4`. https://api.github.com/repos/tailscale/github-action/releases/latest and https://github.com/tailscale/github-action
- Auth methods (README and KB):
  - OAuth client: `oauth-client-id` + `oauth-secret` + `tags: tag:ci`; needs the writable `auth_keys` scope; "an OAuth client secret must be stored as a privileged, sensitive secret value." https://tailscale.com/kb/1276/tailscale-github-action
  - Federated OIDC identity ("recommended" by the KB page): `oauth-client-id` + `audience` + `tags`, workflow needs `id-token: write` ("required for the tailscale action to request a JWT from GitHub"); the client ID and audience are not sensitive; requires Tailscale 1.90.1 or later per the README. https://github.com/tailscale/github-action and https://tailscale.com/kb/1276/tailscale-github-action
  - Auth key: `authkey`; the KB says use reusable, ephemeral, tagged, pre-approved keys; README ties auth keys to Tailnet Lock (`statedir`). Auth keys expire after 90 days ("You cannot generate long-lived auth keys, because they expire after 90 days" - https://tailscale.com/kb/1215/oauth-clients).
- WIF details: Tailscale generates the audience (`api.tailscale.com/<client ID>`); you configure Issuer, Subject (attributes the workload must match) and optional custom claims with `*` wildcards. https://tailscale.com/kb/1581/workload-identity-federation GitHub's OIDC token `sub` can be `repo:OWNER/REPO:environment:NAME` (example `repo:octo-org/octo-repo:environment:prod`), issuer `https://token.actions.githubusercontent.com`. https://docs.github.com/en/actions/concepts/security/openid-connect So the subject can be restricted to an environment, e.g. only the protected `production` environment. (Mapping of this onto Tailscale's Subject field is my inference; the Tailscale page did not show a GitHub example in what I read.)
- Ephemeral/tags: nodes are marked Ephemeral and removed after the run; "At least one tag is required" for OAuth/federated credentials; "the tags specified with `tags` must match all tags on the trust credential" (or be tags owned by those tags); with Device Approval, nodes are also Preapproved. `ping` waits up to 3 minutes for a connection. Runner image >= 2.237.1 required. https://github.com/tailscale/github-action
- ACL side: tags must already exist in the tailnet (`tagOwners`); tagOwners examples take the form `"tag:webserver": ["group:engineering"]`, owners can be users, groups, autogroups or other tags. A grant needs `src`, `dst`, and `ip`; example `"src": ["group:sre"], "dst": ["tag:prod"], "ip": ["*"]`. https://tailscale.com/kb/1337/acl-syntax I did not fetch an example specific to a CI node; a least-privilege grant would be `src: tag:ci`, `dst: <VM tag or IP>`, `ip: ["tcp:22"]` (my construction using the documented fields; verify port syntax in the grants docs).
- SSH: either normal sshd over the tailnet (needs a key/known_hosts secret in Actions) or Tailscale SSH: `tailscale set --ssh` on the host, requires both a network grant and an `ssh` rule; "An SSH access rule from a tagged device cannot be in check mode" (so use `accept`); `users` lists allowed existing local usernames; server only on Linux/macOS (open source variant). Rule example: `"action": "accept", "src": [...], "dst": ["tag:prod"], "users": ["ubuntu","root"]`. https://tailscale.com/kb/1193/tailscale-ssh The VM would need to be tagged (a tagged VM is a requirement for tagged-to-tagged SSH per the page).
- Inbound exposure of the VM: none. The runner and the VM both dial out to Tailscale. (Inference from the architecture; consistent with ephemeral node semantics above.)

### (b) Self-hosted runner on the VM
- GitHub: "We recommend that you only use self-hosted runners with private repositories"; "forks of your public repository can potentially run dangerous code on your self-hosted runner machine." https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/add-runners
- "Self-hosted runners for GitHub do not have guarantees around running in ephemeral clean virtual machines"; avoid them for public repos; JIT runners "perform at most one job before being automatically removed". https://docs.github.com/en/actions/reference/security/secure-use
- Ephemeral: `--ephemeral` with `config.sh`; runner de-registered after one job; JIT runners via the REST API; GitHub recommends autoscaling with ephemeral runners. https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/autoscaling-with-self-hosted-runners
- Fork risk mitigations (settings): "By default, all first-time contributors require approval to run workflows"; option "Require approval for all external contributors". https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository Note this only gates runs; the runner is still on the VM that holds the data.
- Inbound exposure: none (runner polls GitHub outbound). I did not fetch a source for the polling mechanism, so this is from general knowledge (see Unverified).
- Blast radius: code running in a job runs as the runner user on the production VM; if that user is in the `docker` group it is effectively root.

### (c) Pull-based updates
- Watchtower (`containrrr/watchtower`): "This repository was archived by the owner on Dec 17, 2025. It is now read-only." and "This project is no longer maintained". Purpose: "automating Docker container base image updates"; pulls a new image, stops the old container, restarts with original options; Quick Start mounts `/var/run/docker.sock`. https://github.com/containrrr/watchtower (GitHub API also reports `archived: true`, `pushed_at: 2025-12-17`).
- systemd timer / cron `git pull` + `docker compose up -d --build`: no source to cite beyond ordinary tooling; it needs no inbound access and no credentials in GitHub, but the VM must read the (public) repo and, if using ghcr, pull the image (public image: anonymous pull, below).
- Watchtower only works with registry-pulled images, so it requires option 4's ghcr flow; a git-poll script works with on-VM builds.
- A poll-based approach can gate on CI: the script could check the commit status via the GitHub API (my suggestion, not sourced).

### Inbound exposure summary
| Option | Inbound to VM? |
|---|---|
| (a) ephemeral Tailscale node + SSH | None; VM stays tailnet-only (SSH reached over tailnet) |
| (b) self-hosted runner | None |
| (c) pull-based | None |

---

## 4. Image build: on the VM vs GitHub Actions + ghcr.io

### Building in Actions and pushing to ghcr.io
- Official workflow: permissions `contents: read`, `packages: write`, `attestations: write`, `id-token: write`; login `docker/login-action` with `registry: ghcr.io`, `username: ${{ github.actor }}`, `password: ${{ secrets.GITHUB_TOKEN }}` ("You can use the automatically-generated `GITHUB_TOKEN` secret for the password"); `docker/metadata-action` with `images: ghcr.io/${{ github.repository }}`; `docker/build-push-action` with `context: .`, `push: true`, `tags: ${{ steps.meta.outputs.tags }}`, `labels: ${{ steps.meta.outputs.labels }}`. The page pins by SHA and says "GitHub recommends pinning actions to a commit SHA". https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images (attestation steps are optional; `attestations`/`id-token` are only needed for those).
- Versions: build-push-action v7.4.0, metadata-action v6.2.0, login-action v4.8.0, setup-buildx-action v4.4.1 (GitHub API latest releases; README shows `@v7`, `@v6`, `@v4`, `@v4`). https://github.com/docker/build-push-action https://github.com/docker/metadata-action
- Tagging: `type=sha` outputs "Git short commit ... like `sha-860c190`" (default prefix `sha-`, 7 chars). The `latest` tag is generated by default (auto mode) only for `type=ref,event=tag`, `type=semver`, `type=pep440`, `type=match`; so a branch push does not produce `latest` unless you ask (`flavor`/`type=raw,value=latest`; the raw/flavor syntax was not quoted by my fetch, see Unverified). https://github.com/docker/metadata-action
- Layer caching: `cache-from: type=gha` / `cache-to: type=gha,mode=max`; only usable inside a workflow; read-only triggers like `pull_request_target` cannot write (keep `cache-from`, drop `cache-to`); alternative `type=registry,ref=...:buildcache`. https://docs.docker.com/build/ci/github-actions/cache/
- Visibility: "When you first publish a package, the default visibility is private." Public images "can be pulled anonymously". Linking a package to a repo is possible in UI or CLI. Pull with a PAT (classic) needs `read:packages`. https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry
- Pricing: "GitHub Packages usage is free for public packages", and "Container image storage and bandwidth for the Container registry is currently free" (with a promise of one month's notice of any change). Actions: "GitHub Actions usage is free for standard GitHub-hosted runners in public repositories, and for self-hosted runners." https://docs.github.com/en/billing/concepts/product-billing/github-packages ; https://docs.github.com/en/actions/concepts/billing-and-usage
- How the VM pulls: if the package is public, no login. If private, `docker login ghcr.io` with a PAT (classic) with `read:packages` stored on the VM. The image contains the app code, which is already public in this repo, so a public package leaks nothing new (assuming no secrets are baked in; the Dockerfile was not audited here).
- Compose reference: `image` format `[<registry>/][<project>/]<image>[:<tag>|@<digest>]`; `pull_policy` values include `always`, `never`, `missing`, `build`, `daily`, `weekly`, `every_<duration>`; `image` may be omitted if `build` is declared. https://raw.githubusercontent.com/compose-spec/compose-spec/main/spec.md Pointing compose at `ghcr.io/jfbra/the_logbook:sha-<short>` (parameterised by an env var) gives deterministic deploys and rollbacks. Note: image path must be lowercase for ghcr; this is from general knowledge, not fetched.

### Building on the VM (status quo)
- `docker compose up -d --build` needs no registry, no tokens, and no CI-to-VM artifact transfer; the cost is build time on the VM and that the deployed image is not the one CI tested. Rollback = `git checkout <sha>` and rebuild (rebuild may differ if base images/deps drift, though uv.lock pins Python deps).

---

## 5. Security and operations

### Secrets and forks
- "secrets are not passed to the runner when a workflow is triggered from a forked repository" (exception: `GITHUB_TOKEN`). https://docs.github.com/en/actions/how-tos/security-for-github-actions/security-guides/using-secrets-in-github-actions
- `pull_request` from forks: "The `GITHUB_TOKEN` has read-only permissions in pull requests from forked repositories." `pull_request_target` "runs in the context of the default branch of the base repository" and "Running untrusted code on the `pull_request_target` trigger may lead to security vulnerabilities" (same for `workflow_run`). https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
- Secure-use guide: avoid `pull_request_target` unless necessary; don't check out untrusted code in it; pass untrusted input through an env var rather than interpolating into scripts; don't store structured (JSON/XML/YAML) secrets; "automatic redaction is not guaranteed". https://docs.github.com/en/actions/reference/security/secure-use
- The "Send secrets / write tokens to workflows from pull requests" fork settings are described as for private repositories only. https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository
- Design rule: run CI on `pull_request` (no secrets needed: the Postgres credentials are throwaway); run deploy only on `push` to `master` (or `workflow_dispatch`).
- Default `GITHUB_TOKEN` for personal-account repos: read access for `contents` and `packages` unless set permissive. Same settings page. Still declare `permissions:` explicitly.

### Environments protecting the deploy job
- Required reviewers: "up to 6 people or teams", one approval suffices; "Prevent self-review" option; "specify what branches and tags can deploy to this environment"; environment secrets "only available to workflow jobs that use the environment"; wait timer; "A job that references an environment must follow any protection rules ... before running or accessing the environment's secrets." "Users with GitHub Free plans can only configure environments for public repositories" (this repo is public). https://docs.github.com/en/actions/how-tos/managing-workflow-runs-and-deployments/managing-deployments/managing-environments-for-deployment
- For a solo owner, "Prevent self-review" would block the only reviewer from approving; leave it off, or restrict deployment branches to `master` and skip reviewers. (Interaction inferred from the options; not tested.)
- Environment secrets in a personal repo can only be created by the owner. https://docs.github.com/en/actions/how-tos/security-for-github-actions/security-guides/using-secrets-in-github-actions

### Pinning, permissions, Dependabot
- "Pin references to actions to a commit SHA in your workflow files"; set token default read-only and raise per job. https://docs.github.com/en/actions/reference/security/secure-use
- Dependabot: `package-ecosystem: "github-actions"`, `directory: "/"`, `schedule: interval: "weekly"` opens PRs to update action references. https://docs.github.com/en/code-security/dependabot/working-with-dependabot/keeping-your-actions-up-to-date-with-dependabot Whether Dependabot rewrites SHA pins while keeping the `# vX` comment is not stated on that page (see Unverified).

### Migrations on deploy
- Django's migrations docs: migrations are made once in development and "then running the same migrations on ... your staging machines, and eventually your production machines"; commit model change and migration together; on PostgreSQL "all migration operations will run inside a single transaction by default" (unless `atomic = False`); migrations can be reversed by `migrate <app> <previous>`, but "A migration is irreversible if it contains any irreversible operations" (e.g. `RunPython` without reverse code); "migration files ... should run unchanged on Django X.Y+1 ... does not promise forwards-compatibility". https://docs.djangoproject.com/en/6.0/topics/migrations/
- That page has no guidance on running `migrate` as a separate deploy step vs on container start, nor on rolling deploys; it only gives the squash staged-release process (squash, release, wait until all systems upgraded, remove old files, release again). Same page.
- Risk with migrate-on-start (analysis, not sourced): after a code rollback the database stays at the newer schema; the old code may break against it; a failed migration leaves the new container restarting in a loop (PostgreSQL's transactional DDL means a failed migration rolls back its own transaction, per the quote above). With one VM and one container, concurrent migration runners are not a concern; with `docker compose up -d` the old container is replaced, so there is a short downtime window.
- Practical rule: keep migrations backwards compatible for one release (add nullable columns before use; drop columns a release later), so rolling the image back one version still works.

### Rollback
- Registry flow: set the image tag to a previous `sha-<short>` and `docker compose up -d`. Build-on-VM flow: `git checkout <sha>` and `--build`. Schema is not rolled back automatically; reverse with `migrate` only if migrations are reversible, or restore the dump.

### Backup before an automated deploy
- Django's deployment checklist: "If you haven't set up backups for your database, do it right now!" https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/
- `pg_dump` "makes consistent backups even if the database is being used concurrently ... does not block other users accessing the database"; `-Fc` custom format is compressed and restored with `pg_restore`. https://www.postgresql.org/docs/17/app-pgdump.html
- A deploy script step `docker compose exec -T db pg_dump -U logbook -Fc logbook > backup-$(date +%F-%H%M).dump` before `up -d` (command is my construction from the documented flags; keep dumps off the same disk eventually). Backups are not yet set up for this project, so an automated deploy should not ship before at least this pre-deploy dump exists.

---

## Comparison of deploy options

| | (a) Ephemeral Tailscale node + SSH from hosted runner | (b) Self-hosted runner on VM | (c1) VM polls git (timer/cron) | (c2) Watchtower + ghcr |
|---|---|---|---|---|
| What runs where | CI on GitHub; deploy commands over tailnet SSH | CI and deploy jobs run on the VM | Script on VM does `git pull` + compose | Container on VM pulls new image tags |
| Inbound exposure of VM | None | None | None | None |
| Secrets needed | Tailscale OIDC client ID + audience (not sensitive) or OAuth secret/authkey (sensitive); SSH key if not Tailscale SSH | Runner registration token only | None in GitHub; read access to a public repo | None if image is public; PAT `read:packages` if private |
| Blast radius if compromised | Whoever can run the deploy job can reach what ACL grants allow; limit via tag + grant + environment | Any job (incl. fork PR if misconfigured) executes on the production host | Only what lands on `master`; CI results not enforced unless scripted | Anyone able to push the image tag; project archived (no fixes) |
| Setup effort | Medium (ACL tags, grant, OIDC credential, workflow, SSH config) | Medium (install runner, hardening) | Low | Low-medium; needs ghcr flow |
| Fit for single-user homelab | Good: deploy only after CI passes, auditable | Poor for a public repo per GitHub's own advice | Good for simplicity; no deploy-gating | Poor: archived, unmaintained |

---

## Unverified / could not confirm

- Whether the required-status-check name for rulesets is the job `name:` or `workflow / job`; pages I read said only "enter each check's name".
- Whether repository rulesets are available on a free personal public repo: the about-rulesets page says Team/Enterprise; the creating-rulesets page ties only org-level rulesets to those plans. The owner's UI offering conversion suggests yes, but this is not documented in what I read. Check the settings page.
- Exact bypass behaviour of an admin under a classic rule vs ruleset beyond what is quoted (the fetch tool flagged an inconsistency in the "admins are always able to push" wording).
- `postgres` image env vars (`POSTGRES_USER`, `POSTGRES_DB`) and whether `pg_isready` needs `-U` : Docker Hub page not fetched; GitHub docs example sets only `POSTGRES_PASSWORD`.
- `type=raw,value=latest` / `flavor` syntax for metadata-action: the fetch did not return it.
- Whether Dependabot updates SHA-pinned actions with `# vX` comments.
- That a self-hosted runner polls GitHub outbound only (no inbound needed): I did not fetch the page that says so.
- ghcr lowercase image-name requirement: not fetched.
- Tailscale `ip: ["tcp:22"]` grant syntax and the GitHub-environment OIDC `sub` to Tailscale Subject mapping: not shown in what I read.
- Whether WIF in Tailscale is beta/GA and its plan requirements: the page states neither (last validated Jan 30, 2026).
- Compose `build` + `image` together ("image names the built image"): the spec page text I read was truncated at 100000 of 135396 characters; only the sentence "image may be omitted ... as long as a build section is declared" was seen.
- The Dockerfile and compose file in the repo were not reviewed for this research.
- `gh` CLI was not installed here, so release versions came from the public GitHub REST API via curl.

## Decisions this leaves open for the owner

1. Does CI gate merges with a required check and 0 required approvals, with or without an owner bypass ("For pull requests only")? Ruleset or keep the classic rule?
2. Is CI-only (no automated deploy) enough for now, keeping the manual `git pull && docker compose up -d --build`?
3. If automating deploy: push (GitHub reaches into the tailnet, option a) or pull (VM fetches, option c1)? Is a Tailscale credential in GitHub acceptable, and OIDC federation or an OAuth client?
4. Should the deployed image be built in CI and pushed to ghcr.io (public package?), or keep building on the VM?
5. Should the deploy job sit behind an Environment (branch restriction only, or a reviewer given a solo owner)?
6. How should migrations run on deploy: keep migrate-on-start, or a separate pre-deploy step; how strictly to apply the one-release backwards-compatibility rule?
7. Where do pre-deploy `pg_dump` backups go, and how many are retained? Should automated deploy wait until backups exist?
8. Pin actions by SHA with Dependabot, or tags only?

## Researcher's lean (opinion, not sourced)

Start with CI only (job on `pull_request` and `push`, no `paths:` filter, required in a ruleset with 0 approvals), plus Dependabot for actions and SHA pins. Defer automated deploy until backups exist; when adding it, a `workflow_dispatch`/`push`-to-master deploy job in a `production` environment using Tailscale OIDC federation with a tightly scoped `tag:ci` grant is the option that keeps the VM free of inbound exposure and avoids running untrusted code on it. Avoid Watchtower (archived) and a self-hosted runner on a public repo.
