# Build and release process

## Publishing development commits to TestPyPI

Automatic publishing to TestPyPI is done via GitHub Actions from the `dev` branch. To trigger the process, push a commit to the `dev` branch. Make sure to bump the version number first:

```Shell
hatch version # this will show the current version
hatch version patch # or "rc" for a release candidate
```

## Publishing releases to PyPI

Automatic publishing to PyPI is done via GitHub Actions from the `main` branch for tag pushes that starts with `v`. Make sure to bump the version number first:

```Shell
hatch version # this will show the current version
hatch version patch # or "minor" or "rc" depending on where you are in the release cycle
```