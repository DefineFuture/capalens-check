# Releasing

Publication is a decision of the project owner (南京定义未来科技有限公司). Nothing in this repository publishes
by itself: the release workflow runs only when a maintainer pushes a version tag, and PyPI publishing waits for
approval on the `pypi` environment.

## First publication (once)

1. **Approve publication** and the public name (`capalens-check`, repository `DefineFuture/capalens-check`).
2. **Name the maintainers** (at least two people) and create the `DefineFuture/maintainers` team used in
   `.github/CODEOWNERS`.
3. **Re-check the documents that describe other projects**: `docs/comparison.md` (names, links, current
   behaviour) and every specification link in `src/capalens_check/checks.py`.
4. **Create the repository** `DefineFuture/capalens-check` (public), then in its settings:
   * Branch protection on `main`: pull requests required, CI required, at least one review, no force pushes.
   * Security: enable private vulnerability reporting, Dependabot alerts and security updates, secret scanning
     and push protection, code scanning (CodeQL default setup).
   * Actions: default `GITHUB_TOKEN` read-only; require approval for workflows from first-time contributors.
   * Environment `pypi` with required reviewers (the maintainers).
5. **PyPI**: create the project `capalens-check` as a pending trusted publisher (owner `DefineFuture`, repository
   `capalens-check`, workflow `release.yml`, environment `pypi`). No API token is stored anywhere.
6. **Pin actions** in `.github/workflows/*.yml` and `action.yml` to full commit SHAs (keep the version as a
   comment); Dependabot keeps them current.
7. Push the code, wait for CI to pass on all platforms.

## Every release

1. Update `CHANGELOG.md`: move "Unreleased" entries under `## [x.y.z] - YYYY-MM-DD`.
2. Set the version in `pyproject.toml`, `src/capalens_check/__init__.py` and `CITATION.cff`.
3. Regenerate the catalogue if checks changed: `capalens-check checks --format markdown > docs/checks.md`.
4. Open a pull request, merge when CI passes.
5. Tag and push: `git tag -s vX.Y.Z -m "capalens-check X.Y.Z" && git push origin vX.Y.Z`.
6. Approve the `pypi` deployment. The workflow builds, tests, publishes to PyPI and creates the GitHub release
   with the changelog section as notes.
7. Move the major action tag: `git tag -f v0 vX.Y.Z && git push -f origin v0` (users of `@v0` get the update).
8. Optional: list the action on the GitHub Marketplace (first release only, from the release page).

## Versioning

Semantic versioning. Before 1.0, a minor version may change what a check considers a pass; check ids never
change meaning. Adding a check is a minor version; fixing a false positive is a patch.
