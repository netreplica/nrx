# Claude Code Instructions for nrx Repository

## Python Environment

**Use the development virtual environment for all operations:**
```bash
source ./nrx310-dev/bin/activate
```

**Do NOT use:**
- `~/.venv/nrx310` - This is for production testing only
- `./nrx310` - Wrong environment

## Running Tests

### Unit Tests
```bash
make unit-test
```

Unit tests are located in `tests/unit/` and use pytest.

### Linting
```bash
make lint
```

Must achieve **10.00/10** rating with no warnings to pass CI.

### System Tests
```bash
make test          # All system tests
make test-local    # Tests requiring NetBox
```

## Code Quality Standards

1. **Pylint**: Must score 10.00/10
   - Extract helper functions if cyclomatic complexity > 12 branches
   - Follow PEP 8 conventions
   - Avoid implicit booleanness comparisons in tests (use `not x` instead of `x == []`)

2. **Testing**: All new functionality requires unit tests
   - Place in `tests/unit/`
   - All tests must pass before committing
   - Use descriptive test names and docstrings

3. **Documentation**: Update relevant docs
   - `docs/TESTING.md` - For testing changes
   - `README.md` - For user-facing changes

## Git Workflow

### Branch Strategy
- `main` - Production releases
- `dev` - Development branch (default target for PRs)
- Feature branches - Named descriptively (e.g., `export-error-nonetype`)

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
1. Push branch to origin
2. Create PR targeting `dev` branch
3. Include comprehensive summary with:
   - Bug fixes
   - New features
   - Test coverage
   - Breaking changes (if any)

## CI/CD Pipeline

GitHub Actions run on push/PR:
1. **Pylint** - Python 3.10, 3.11
2. **Unit Tests** - Python 3.10, 3.11
3. **System Tests** - Integration tests

All must pass before merging.

## Project Structure

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

## Common Commands

```bash
# Development setup
python3.9 -m venv nrx310-dev
source nrx310-dev/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

# Run all checks before committing
make lint
make unit-test

# Build package
make build

# Clean build artifacts
make clean
```

## Debugging

### Run with debug output
```bash
nrx --debug --config ~/.nr/config.conf [other args]
```

### Test specific functionality
```bash
# Config loading
PYTHONPATH=./src python -c "from nrx.nrx import load_toml_config; print(load_toml_config('config.conf'))"

# Unit test specific file
PYTHONPATH=./src pytest tests/unit/test_config.py -v
```

## Special Considerations

### Backward Compatibility
- Maintain compatibility with older config files
- Support both old and new parameter names (e.g., `EXPORT_SITE` and `EXPORT_SITES`)
- Document breaking changes prominently

### NetBox Integration
- Test against multiple NetBox versions (see `make test-previous`, `test-current`, `test-latest`)
- Handle API version differences gracefully

### Code Organization
- Keep functions under 12 branches for pylint
- Extract helper functions when complexity grows
- Use descriptive variable names
- Add docstrings to all public functions

## Notes
- Always activate `nrx310-dev` virtual environment
- Run `make lint` and `make unit-test` before committing
- Target `dev` branch for pull requests
- Maintain 10.00/10 pylint score
