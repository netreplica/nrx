# Contributing to nrx

Thank you for your interest in contributing to nrx! This guide will help you get started.

## Development Setup

### Prerequisites

* Python 3.10 or higher
* Git
* Make

### Clone the Repository

```bash
git clone https://github.com/netreplica/nrx.git --recursive
cd nrx
```

The `--recursive` flag is important as it includes the templates submodule.

### Set Up Development Environment

According to the [project instructions](https://github.com/netreplica/nrx/blob/main/CLAUDE.md), use the development virtual environment:

```bash
python3.10 -m venv nrx310-dev
source nrx310-dev/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

!!! warning "Environment Selection"
    Always use `nrx310-dev` for development. Do NOT use:

    * `~/.venv/nrx310` - Production testing only
    * `./nrx310` - Wrong environment

### Verify Installation

```bash
nrx --version
make unit-test
make lint
```

## Code Quality Standards

### Pylint Requirements

All code must achieve a **10.00/10** pylint score to pass CI:

```bash
make lint
```

#### Complexity Guidelines

* Extract helper functions if cyclomatic complexity > 12 branches
* Follow PEP 8 conventions
* Avoid implicit booleanness comparisons in tests (use `not x` instead of `x == []`)

### Testing Requirements

All new functionality requires unit tests:

* Place tests in `tests/unit/`
* All tests must pass before committing
* Use descriptive test names and docstrings

Run tests:

```bash
make unit-test
```

For more details, see [Testing Documentation](testing.md).

## Development Workflow

### Branch Strategy

* `main` - Production releases
* `dev` - Development branch (default target for PRs)
* Feature branches - Named descriptively (e.g., `feature/export-error-handling`)

### Making Changes

1. Create a feature branch from `dev`:
   ```bash
   git checkout dev
   git pull origin dev
   git checkout -b feature/your-feature-name
   ```

2. Make your changes

3. Run quality checks:
   ```bash
   make lint
   make unit-test
   ```

4. Commit your changes following the [commit message format](#commit-messages)

5. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

### Commit Messages

Follow this format:

```
Short descriptive title (50 chars max)

- Bullet point details
- What changed and why
- Related issue references

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### Creating Pull Requests

1. Push your branch to origin
2. Create a PR targeting the `dev` branch
3. Include a comprehensive summary with:
   * Bug fixes
   * New features
   * Test coverage
   * Breaking changes (if any)

## CI/CD Pipeline

GitHub Actions run on push/PR:

1. **Pylint** - Python 3.10, 3.11
2. **Unit Tests** - Python 3.10, 3.11
3. **System Tests** - Integration tests

All must pass before merging.

## Code Organization

### Project Structure

```
nrx/
├── src/nrx/          # Source code
│   └── nrx.py        # Main application
├── tests/
│   ├── unit/         # Unit tests (pytest)
│   ├── dc1/          # System test fixtures
│   └── ...
├── docs/             # Documentation
├── .github/
│   └── workflows/    # CI/CD workflows
├── Makefile          # Build commands
└── requirements*.txt # Dependencies
```

### Best Practices

* Keep functions under 12 branches for pylint
* Extract helper functions when complexity grows
* Use descriptive variable names
* Add docstrings to all public functions

## Documentation

Update relevant documentation for your changes:

* `docs/` - User-facing documentation
* `README.md` - For major feature changes
* Docstrings - For all public functions

### Building Documentation

```bash
# Install docs dependencies
pip install -r requirements-dev.txt

# Serve locally
mkdocs serve

# Build static site
mkdocs build
```

## Debugging

### Run with Debug Output

```bash
nrx --debug --config ~/.nr/config.conf [other args]
```

### Test Specific Functionality

```bash
# Config loading
PYTHONPATH=./src python -c "from nrx.nrx import load_toml_config; print(load_toml_config('config.conf'))"

# Unit test specific file
PYTHONPATH=./src pytest tests/unit/test_config.py -v
```

## Special Considerations

### Backward Compatibility

* Maintain compatibility with older config files
* Support both old and new parameter names
* Document breaking changes prominently

### NetBox Integration

* Test against multiple NetBox versions
* Handle API version differences gracefully
* See `make test-previous`, `test-current`, `test-latest` for version testing

## Using uv for Development

For faster local development with uv:

```bash
# Install in editable mode
uv pip install -e .

# Run from source
uv run nrx --version

# Run tests
uv run pytest tests/unit/ -v
```

## Getting Help

* Join our [Discord server](https://discord.gg/M2SkgSdKht)
* Check [#netreplica](https://netdev-community.slack.com/archives/C054GKBC4LB) on NetDev Community Slack
* Open a [GitHub issue](https://github.com/netreplica/nrx/issues)

## Code Review Process

1. All PRs require review before merging
2. Address review comments promptly
3. Keep PRs focused and reasonably sized
4. Update PR description if scope changes

## Release Process

Releases are managed by maintainers:

1. Version bump in `src/nrx/__about__.py`
2. Update `CHANGELOG.md`
3. Tag release in git
4. Publish to PyPI via GitHub Actions
5. Update documentation

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.

## Recognition

Contributors are recognized in:

* Release notes
* GitHub contributors page
* Project documentation

Thank you for contributing to nrx!
