# Testing

## System tests

System tests are divided into two groups:
    * `make test-local` – tests that export data from Netbox and therefore can be run in the local environment with Netbox instances available
    * `make test` – tests that export data from JSON `cyjs` files and can run in any environment, including Github Actions

## Netbox versions

`nrx` is tested against three versions of Netbox:
    * `make test-latest` – currently Netbox 3.6.9
    * `make test-current` – currently Netbox 3.5.3
    * `make test-previous` – currently Netbox 3.4.10

## Running the tests manually

Activate the development environment:

```Shell
python3.9 -m venv nrx39-dev
source nrx39-dev/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

Run the tests:

```Shell
make test
```
