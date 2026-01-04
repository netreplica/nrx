# Build and Release Process

## Overview

The nrx package uses automated publishing workflows via GitHub Actions:

- **TestPyPI** - For testing pre-releases
- **PyPI** - For production releases

## Version Management

Check and update version numbers using hatch:

```bash
hatch version              # Show current version
hatch version patch        # Bump patch version (0.8.0 → 0.8.1)
hatch version minor        # Bump minor version (0.8.1 → 0.9.0)
hatch version rc           # Mark as release candidate (0.8.1 → 0.8.1rc0)
```

After version changes, update `versions.yaml` with the new version.

## Publishing to TestPyPI (Testing)

TestPyPI is used to test package releases before publishing to production PyPI.

### Automated Publishing (Recommended)

Push a pre-release tag to trigger automatic publishing:

```bash
# Update version to rc/dev/alpha/beta
hatch version rc           # Creates version like 0.8.1rc0

# Create and push tag (automated via make)
make test-publish

# Or manually:
git tag v0.8.1rc0 && git push --tags

# GitHub Actions automatically builds and publishes to TestPyPI
```

The `make test-publish` command:
- Checks that version contains rc/dev/alpha/beta
- Creates tag from current version
- Pushes tag to trigger GitHub Actions
- No local build/upload needed

**Supported tag patterns:**
- `v*rc*` - Release candidates (e.g., v0.8.1rc1)
- `v*-dev*` - Development releases (e.g., v0.8.1-dev1)
- `v*-alpha*` - Alpha releases (e.g., v0.8.1-alpha1)
- `v*-beta*` - Beta releases (e.g., v0.8.1-beta1)

### Manual Publishing (Alternative)

For manual testing without GitHub Actions:

```bash
# Build the package
make clean
make build

# Upload to TestPyPI manually
python3 -m twine upload --repository testpypi dist/*

# Test installation
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple nrx
```

**Note:** Manual upload requires PyPI credentials configured in `~/.pypirc`.

## Publishing to PyPI (Production)

Production releases to PyPI are triggered by publishing a GitHub release.

### Automated Publishing (Recommended)

1. **Prepare the release**
   ```bash
   # Update version to final release number
   hatch version release     # Removes rc/dev/alpha/beta suffix

   # Update versions.yaml
   vim versions.yaml

   # Commit version changes
   git add pyproject.toml versions.yaml
   git commit -m "Bump version to v0.8.1"
   git push origin main
   ```

2. **Create GitHub Release**
   - Go to https://github.com/netreplica/nrx/releases/new
   - Click "Choose a tag" → Create new tag: `v0.8.1`
   - Set title: `Release v0.8.1`
   - Add release notes describing changes
   - Click "Publish release"

3. **Automatic deployment**
   - GitHub Actions automatically builds and publishes to PyPI
   - Monitor at: https://github.com/netreplica/nrx/actions

### Manual Publishing (Not Recommended)

Only use manual publishing if automated workflows fail:

```bash
# Build the package
make clean
make build

# Upload to PyPI (requires credentials)
make publish
```

**⚠️ Warning:** Manual publishing bypasses CI/CD checks and should only be used in emergencies.

## Testing Published Packages

### Test from TestPyPI

```bash
# Create test environment
python3 -m venv test-env
source test-env/bin/activate

# Install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple nrx

# Test the installation
nrx --version
```

### Test from PyPI

```bash
# Create test environment
python3 -m venv test-env
source test-env/bin/activate

# Install from PyPI
pip install nrx

# Test the installation
nrx --version
```

## Release Workflow Summary

### Pre-release Testing
1. `hatch version rc` → v0.8.1rc0
2. `make test-publish` → Creates tag and pushes
3. Automatic publish to TestPyPI via GitHub Actions
4. Test installation from TestPyPI
5. Iterate with rc1, rc2, etc. if needed (`hatch version rc` increments automatically)

### Production Release
1. `hatch version release` → v0.8.1
2. Update `versions.yaml`
3. Commit and push to `main`
4. Create GitHub Release with tag `v0.8.1`
5. Automatic publish to PyPI
6. Verify at https://pypi.org/project/nrx/

## Troubleshooting

### Build Artifacts Not Clean
```bash
make clean
make build
```

### Manual Build and Check
```bash
python3 -m build
twine check dist/*
```

### View Package Contents
```bash
tar -tzf dist/nrx-*.tar.gz
unzip -l dist/nrx-*.whl
```

## Make Commands Reference

- `make lint` - Run pylint on source code
- `make unit-test` - Run unit tests
- `make build` - Build distribution packages
- `make test-publish` - Create tag and trigger TestPyPI publish (automated)
- `make publish` - Manually publish to PyPI (requires credentials)
- `make clean` - Remove build artifacts
- `make pubdev` - Legacy alias for `test-publish`

## Required Tools

- `hatch` - Version management and building
- `build` - Package building
- `twine` - Package uploading (for manual publishing)

Install with:
```bash
pip install hatch build twine
```
