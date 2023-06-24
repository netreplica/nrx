lint:
	pylint nrx/*.py

test-local: test-dc1 test-dc2 test-colo test-site1 test-h88
test: test-dc1-cyjs-2-clab test-dc2-cyjs-2-cml test-site1-cyjs-2-clab test-dc1-cyjs-2-graphite test-dc2-cyjs-2-graphite

test-dc1: test-dc1-nb-2-cyjs-current test-dc1-nb-2-cyjs-latest test-dc1-cyjs-2-clab test-dc1-cyjs-2-graphite
test-dc2: test-dc2-nb-2-cyjs-current test-dc2-nb-2-cyjs-latest test-dc2-cyjs-2-cml test-dc2-cyjs-2-graphite
test-colo: test-colo-nb-2-cyjs-current test-colo-nb-2-cyjs-latest
test-site1: test-site1-nb-2-cyjs-current test-site1-nb-2-cyjs-latest test-site1-cyjs-2-clab
test-h88: test-h88-nb-2-cyjs-current test-h88-nb-2-cyjs-latest test-h88-cyjs-2-clab

test-dc1-nb-2-cyjs-current:
	@echo "#################################################################"
	@echo "# DC1: read from NetBox current version and export as CYJS"
	@echo "#################################################################"
	mkdir -p tests/dc1/test && cd tests/dc1/test && rm -f * && \
	source ../.env_current && \
	../../../nrx.py -c ../nrx.conf -o cyjs -d && \
	diff dc1.cyjs ../data/dc1.cyjs
	@echo

test-dc1-nb-2-cyjs-latest:
	@echo "#################################################################"
	@echo "# DC1: read from NetBox latest version and export as CYJS"
	@echo "#################################################################"
	mkdir -p tests/dc1/test && cd tests/dc1/test && rm -f * && \
	source ../.env_latest && \
	../../../nrx.py -c ../nrx.conf -o cyjs -d && \
	diff dc1.cyjs ../data/dc1.cyjs
	@echo

test-dc1-cyjs-2-clab:
	@echo "#################################################################"
	@echo "# DC1: read from CYJS and export as Containerlab"
	@echo "#################################################################"
	mkdir -p tests/dc1/test && cd tests/dc1/test && rm -f * && \
	../../../nrx.py -c ../nrx.conf -i cyjs -f ../data/dc1.cyjs -d && \
	for f in *; do echo Comparing file $$f ...; diff $$f ../data/$$f || exit 1; done
	@echo

test-dc1-cyjs-2-graphite:
	@echo "#################################################################"
	@echo "# DC1: read from CYJS and export as graphite"
	@echo "#################################################################"
	mkdir -p tests/dc1/graphite && cd tests/dc1/graphite && rm -f * && \
	../../../nrx.py -c ../nrx.conf -i cyjs -f ../data/dc1.cyjs -o graphite -d && \
	for f in *; do echo Comparing file $$f ...; diff $$f ../data/$$f || exit 1; done
	@echo

test-dc2-nb-2-cyjs-current:
	@echo "#################################################################"
	@echo "# DC2: read from NetBox current version and export as CYJS"
	@echo "#################################################################"
	mkdir -p tests/dc2/test && cd tests/dc2/test && rm -f * && \
	source ../.env_current && \
	../../../nrx.py -c ../nrx.conf -o cyjs -d && \
	diff dc2.cyjs ../data/dc2.cyjs.current
	@echo

test-dc2-nb-2-cyjs-latest:
	@echo "#################################################################"
	@echo "# DC2: read from NetBox latest version and export as CYJS"
	@echo "#################################################################"
	mkdir -p tests/dc2/test && cd tests/dc2/test && rm -f * && \
	source ../.env_latest && \
	../../../nrx.py -c ../nrx.conf -o cyjs -d && \
	diff dc2.cyjs ../data/dc2.cyjs.latest
	@echo

test-dc2-cyjs-2-graphite:
	@echo "#################################################################"
	@echo "# DC2: read from CYJS and export as graphite"
	@echo "#################################################################"
	mkdir -p tests/dc2/graphite && cd tests/dc2/graphite && rm -f * && \
	../../../nrx.py -c ../nrx.conf -i cyjs -f ../data/dc2.cyjs -o graphite -d && \
	for f in *; do echo Comparing file $$f ...; diff $$f ../data/$$f || exit 1; done
	@echo

test-dc2-cyjs-2-cml:
	@echo "#################################################################"
	@echo "# DC2: read from CYJS and export as CML"
	@echo "#################################################################"
	mkdir -p tests/dc2/test && cd tests/dc2/test && rm -f * && \
	../../../nrx.py -c ../nrx.conf -i cyjs -f ../data/dc2.cyjs -d && \
	for f in *; do echo Comparing file $$f ...; diff $$f ../data/$$f || exit 1; done
	@echo

test-colo-nb-2-cyjs-current:
	@echo "#################################################################"
	@echo "# Colo: read from NetBox current version and export as CYJS"
	@echo "#################################################################"
	mkdir -p tests/colo/test && cd tests/colo/test && rm -f * && \
	source ../.env_current && \
	../../../nrx.py -c ../nrx.conf -o cyjs -d && \
	diff colo.cyjs ../data/colo.cyjs
	@echo

test-colo-nb-2-cyjs-latest:
	@echo "#################################################################"
	@echo "# Colo: read from NetBox latest version and export as CYJS"
	@echo "#################################################################"
	mkdir -p tests/colo/test && cd tests/colo/test && rm -f * && \
	source ../.env_latest && \
	../../../nrx.py -c ../nrx.conf -o cyjs -d && \
	diff colo.cyjs ../data/colo.cyjs
	@echo

test-site1-nb-2-cyjs-current:
	@echo "#################################################################"
	@echo "# Site1: read from NetBox current version and export as CYJS"
	@echo "#################################################################"
	mkdir -p tests/site1/test && cd tests/site1/test && rm -f * && \
	source ../.env_current && \
	../../../nrx.py -c ../nrx.conf -o cyjs -d && \
	diff site1.cyjs ../data/site1.cyjs
	@echo

test-site1-nb-2-cyjs-latest:
	@echo "#################################################################"
	@echo "# Site1: read from NetBox latest version and export as CYJS"
	@echo "#################################################################"
	mkdir -p tests/site1/test && cd tests/site1/test && rm -f * && \
	source ../.env_latest && \
	../../../nrx.py -c ../nrx.conf -o cyjs -d && \
	diff site1.cyjs ../data/site1.cyjs
	@echo

test-site1-cyjs-2-clab:
	@echo "#################################################################"
	@echo "# Site1: read from CYJS and export as Containerlab"
	@echo "#################################################################"
	mkdir -p tests/site1/test && cd tests/site1/test && rm -f * && \
	../../../nrx.py -c ../nrx.conf -i cyjs -f ../data/site1.cyjs -o clab -d && \
	for f in *; do echo Comparing file $$f ...; diff $$f ../data/$$f || exit 1; done
	@echo

test-site1-cyjs-template-2-clab:
	@echo "#################################################################"
	@echo "# Site1: replace Platform in the template, read from CYJS and export as Containerlab"
	@echo "#################################################################"
	mkdir -p tests/site1/test && cd tests/site1/test && rm -f * && \
	cat ../data/site1.cyjs.template | envsubst > site1.sonic-vs.cyjs && \
	../../../nrx.py -c ../nrx.conf -i cyjs -f site1.sonic-vs.cyjs -o clab -d && \
	for f in *.yaml; do echo Comparing file $$f ...; diff $$f ../data/$$f || exit 1; done
	@echo


test-h88-nb-2-cyjs-current:
	@echo "#################################################################"
	@echo "# h88: read from NetBox current version and export as CYJS"
	@echo "#################################################################"
	mkdir -p tests/h88/test && cd tests/h88/test && rm -f * && \
	source ../.env_current && \
	../../../nrx.py -c ../nrx.conf -o cyjs -d && \
	diff HQ.cyjs ../data/HQ.cyjs.current
	@echo

test-h88-nb-2-cyjs-latest:
	@echo "#################################################################"
	@echo "# h88: read from NetBox latest version and export as CYJS"
	@echo "#################################################################"
	mkdir -p tests/h88/test && cd tests/h88/test && rm -f * && \
	source ../.env_latest && \
	../../../nrx.py -c ../nrx.conf -o cyjs -d && \
	diff HQ.cyjs ../data/HQ.cyjs.latest
	@echo

test-h88-cyjs-2-clab:
	@echo "#################################################################"
	@echo "# h88: read from CYJS and export as Containerlab"
	@echo "#################################################################"
	mkdir -p tests/h88/test && cd tests/h88/test && rm -f * && \
	../../../nrx.py -c ../nrx.conf -i cyjs -f ../data/HQ.cyjs -o clab -d && \
	for f in *; do echo Comparing file $$f ...; diff $$f ../data/$$f || exit 1; done
	@echo

