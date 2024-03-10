lint:
	pylint nrx/*.py

build:
	python3 -m build

publish:
	python3 -m twine upload --repository testpypi dist/*

clean:
	rm dist/*

test-local: test-dc1 test-dc2 test-colo test-site1 test-h88
test-local-lrg: test-lrg-nb-2-cyjs-latest
test-current: test-dc1-nb-2-cyjs-current test-dc2-nb-2-cyjs-current test-colo-nb-2-cyjs-current test-site1-nb-2-cyjs-current test-h88-nb-2-cyjs-current
test-latest: test-dc1-nb-2-cyjs-latest test-dc2-nb-2-cyjs-latest test-colo-nb-2-cyjs-latest test-site1-nb-2-cyjs-latest test-h88-nb-2-cyjs-latest
test: test-args test-dc1-cyjs-2-clab test-dc1-cyjs-2-clab-custom-platform-map test-dc2-cyjs-2-cml test-site1-cyjs-2-clab test-site1-cyjs-2-clab-rename test-dc1-cyjs-2-graphite test-dc2-cyjs-2-graphite test-h88-cyjs-2-clab test-dc1-cyjs-2-d2 test-lrg-cyjs-2-graphite

test-args: test-args-site-and-sites
test-clab: test-dc1-cyjs-2-clab test-dc1-cyjs-2-clab-custom-platform-map test-site1-cyjs-2-clab test-h88-cyjs-2-clab
test-cml: test-dc2-cyjs-2-cml
test-graphite: test-dc1-cyjs-2-graphite test-dc2-cyjs-2-graphite test-lrg-cyjs-2-graphite
test-d2: test-dc1-cyjs-2-d2

test-dc1: test-dc1-nb-2-cyjs-current test-dc1-nb-2-cyjs-latest test-dc1-cyjs-2-clab test-dc1-cyjs-2-clab-custom-platform-map test-dc1-cyjs-2-graphite test-dc1-cyjs-2-d2
test-dc2: test-dc2-nb-2-cyjs-current test-dc2-nb-2-cyjs-latest test-dc2-cyjs-2-cml test-dc2-cyjs-2-graphite
test-colo: test-colo-nb-2-cyjs-current test-colo-nb-2-cyjs-latest
test-site1: test-site1-nb-2-cyjs-current test-site1-nb-2-cyjs-latest test-site1-cyjs-2-clab test-site1-cyjs-2-clab-rename
test-h88: test-h88-nb-2-cyjs-current test-h88-nb-2-cyjs-latest test-h88-nb-2-cyjs-latest-noconfigs test-h88-cyjs-2-clab
test-lrg: test-lrg-nb-2-cyjs-latest test-lrg-cyjs-2-graphite

test-args-site-and-sites:
	@echo "#################################################################"
	@echo "# Simulteneous use of site and sites should fail"
	@echo "#################################################################"
	! ./nrx.py --site dc1 --sites dc1,dc2 -d
	@echo

test-dc1-nb-2-cyjs-current:
	@echo "#################################################################"
	@echo "# DC1: read from NetBox current version and export as CYJS"
	@echo "#################################################################"
	mkdir -p tests/dc1/test && cd tests/dc1/test && rm -rf * && \
	source ../../.env_current && \
	../../../nrx.py -c ../nrx.conf -o cyjs -d && \
	diff dc1.cyjs ../data/dc1.cyjs
	@echo

test-dc1-nb-2-cyjs-latest:
	@echo "#################################################################"
	@echo "# DC1: read from NetBox latest version and export as CYJS"
	@echo "#################################################################"
	mkdir -p tests/dc1/test && cd tests/dc1/test && rm -rf * && \
	source ../../.env_latest && \
	../../../nrx.py -c ../nrx.conf -o cyjs -d && \
	diff dc1.cyjs ../data/dc1.cyjs
	@echo

test-dc1-nb-2-cyjs-single-site:
	@echo "#################################################################"
	@echo "# Single site DC1: read from NetBox current version and export as CYJS"
	@echo "#################################################################"
	mkdir -p tests/dc1/test && cd tests/dc1/test && rm -rf * && \
	source ../../.env_current && \
	../../../nrx.py -c ../nrx-no-site.conf -o cyjs --site dc1 -d && \
	diff dc1.cyjs ../data/dc1.cyjs
	@echo

test-dc1-nb-2-cyjs-single-sites:
	@echo "#################################################################"
	@echo "# Single site DC1: read from NetBox current version and export as CYJS"
	@echo "#################################################################"
	mkdir -p tests/dc1/test && cd tests/dc1/test && rm -rf * && \
	source ../../.env_current && \
	../../../nrx.py -c ../nrx-no-site.conf -o cyjs --sites dc1 -d && \
	diff dc1.cyjs ../data/dc1.cyjs
	@echo

test-dc1-dc2-nb-2-cyjs-sites:
	@echo "#################################################################"
	@echo "# Two site DC1 and DC2: read from NetBox current version and export as CYJS"
	@echo "#################################################################"
	mkdir -p tests/dc1/test && cd tests/dc1/test && rm -rf * && \
	source ../../.env_current && \
	../../../nrx.py -c ../nrx-no-site.conf -o cyjs --sites dc1,dc2 -d && \
	diff dc1-dc2.cyjs ../data/dc1-dc2.cyjs
	@echo

test-dc1-cyjs-2-clab:
	@echo "#################################################################"
	@echo "# DC1: read from CYJS and export as Containerlab"
	@echo "#################################################################"
	mkdir -p tests/dc1/test && cd tests/dc1/test && rm -rf * && \
	../../../nrx.py -c ../nrx.conf -i cyjs -f ../data/dc1.cyjs -d && \
	for f in *; do echo Comparing file $$f ...; diff $$f ../data/$$f || exit 1; done
	@echo

test-dc1-cyjs-2-clab-custom-platform-map:
	@echo "#################################################################"
	@echo "# DC1: read from CYJS and export as Containerlab using custom platform map"
	@echo "#################################################################"
	mkdir -p tests/dc1/test && cd tests/dc1/test && rm -rf * && \
	../../../nrx.py -c ../nrx.conf -i cyjs -f ../data/dc1.cyjs -M ../platform_map.yaml -d && \
	for f in *; do echo Comparing file $$f ...; diff $$f ../custom-clab/$$f || exit 1; done
	@echo

test-dc1-cyjs-2-graphite:
	@echo "#################################################################"
	@echo "# DC1: read from CYJS and export as graphite"
	@echo "#################################################################"
	mkdir -p tests/dc1/graphite && cd tests/dc1/graphite && rm -rf * && \
	../../../nrx.py -c ../nrx.conf -i cyjs -f ../data/dc1.cyjs -o graphite -d && \
	for f in *; do echo Comparing file $$f ...; diff $$f ../data/$$f || exit 1; done
	@echo

test-dc1-dc2-cyjs-2-graphite:
	@echo "#################################################################"
	@echo "# DC1 and DC2: read from CYJS and export as graphite"
	@echo "#################################################################"
	mkdir -p tests/dc1/graphite && cd tests/dc1/graphite && rm -rf * && \
	../../../nrx.py -c ../nrx-no-site.conf -i cyjs -f ../data/dc1-dc2.cyjs -o graphite -d && \
	for f in *; do echo Comparing file $$f ...; diff $$f ../data/$$f || exit 1; done
	@echo

test-dc1-cyjs-2-d2:
	@echo "#################################################################"
	@echo "# DC1: read from CYJS and export as d2"
	@echo "#################################################################"
	mkdir -p tests/dc1/d2 && cd tests/dc1/d2 && rm -rf * && \
	../../../nrx.py -c ../nrx.conf -i cyjs -f ../data/dc1.cyjs -o d2 -d && \
	for f in *; do echo Comparing file $$f ...; diff $$f ../data/$$f || exit 1; done
	@echo

update-dc1:
	@echo "#################################################################"
	@echo "# Update reference data for DC1"
	@echo "#################################################################"
	cd tests/dc1/test && \
	cp * ../data/
	@echo

test-dc2-nb-2-cyjs-current:
	@echo "#################################################################"
	@echo "# DC2: read from NetBox current version and export as CYJS"
	@echo "#################################################################"
	mkdir -p tests/dc2/test && cd tests/dc2/test && rm -rf * && \
	source ../../.env_current && \
	../../../nrx.py -c ../nrx.conf -o cyjs -d && \
	diff dc2.cyjs ../data/dc2.cyjs.current
	@echo

test-dc2-nb-2-cyjs-latest:
	@echo "#################################################################"
	@echo "# DC2: read from NetBox latest version and export as CYJS"
	@echo "#################################################################"
	mkdir -p tests/dc2/test && cd tests/dc2/test && rm -rf * && \
	source ../../.env_latest && \
	../../../nrx.py -c ../nrx.conf -o cyjs -d && \
	diff dc2.cyjs ../data/dc2.cyjs.latest
	@echo

test-dc2-cyjs-2-graphite:
	@echo "#################################################################"
	@echo "# DC2: read from CYJS and export as graphite"
	@echo "#################################################################"
	mkdir -p tests/dc2/graphite && cd tests/dc2/graphite && rm -rf * && \
	../../../nrx.py -c ../nrx.conf -i cyjs -f ../data/dc2.cyjs -o graphite -d && \
	for f in *; do echo Comparing file $$f ...; diff $$f ../data/$$f || exit 1; done
	@echo

test-dc2-cyjs-2-cml:
	@echo "#################################################################"
	@echo "# DC2: read from CYJS and export as CML"
	@echo "#################################################################"
	mkdir -p tests/dc2/test && cd tests/dc2/test && rm -rf * && \
	../../../nrx.py -c ../nrx.conf -i cyjs -f ../data/dc2.cyjs -d && \
	for f in *; do echo Comparing file $$f ...; diff $$f ../data/$$f || exit 1; done
	@echo

update-dc2:
	@echo "#################################################################"
	@echo "# Update reference data for DC2"
	@echo "#################################################################"
	cd tests/dc2/test && \
	cp * ../data/
	@echo

test-colo-nb-2-cyjs-current:
	@echo "#################################################################"
	@echo "# Colo: read from NetBox current version and export as CYJS"
	@echo "#################################################################"
	mkdir -p tests/colo/test && cd tests/colo/test && rm -rf * && \
	source ../../.env_current && \
	../../../nrx.py -c ../nrx.conf -o cyjs -d && \
	diff colo.cyjs ../data/colo.cyjs
	@echo

test-colo-nb-2-cyjs-latest:
	@echo "#################################################################"
	@echo "# Colo: read from NetBox latest version and export as CYJS"
	@echo "#################################################################"
	mkdir -p tests/colo/test && cd tests/colo/test && rm -rf * && \
	source ../../.env_latest && \
	../../../nrx.py -c ../nrx.conf -o cyjs -d && \
	diff colo.cyjs ../data/colo.cyjs
	@echo

test-site1-nb-2-cyjs-current:
	@echo "#################################################################"
	@echo "# Site1: read from NetBox current version and export as CYJS"
	@echo "#################################################################"
	mkdir -p tests/site1/test && cd tests/site1/test && rm -rf * && \
	source ../../.env_current && \
	../../../nrx.py -c ../nrx.conf -o cyjs -d && \
	diff site1.cyjs ../data/site1.cyjs
	@echo

test-site1-nb-2-cyjs-latest:
	@echo "#################################################################"
	@echo "# Site1: read from NetBox latest version and export as CYJS"
	@echo "#################################################################"
	mkdir -p tests/site1/test && cd tests/site1/test && rm -rf * && \
	source ../../.env_latest && \
	../../../nrx.py -c ../nrx.conf -o cyjs -d && \
	diff site1.cyjs ../data/site1.cyjs
	@echo

test-site1-cyjs-2-clab:
	@echo "#################################################################"
	@echo "# Site1: read from CYJS and export as Containerlab"
	@echo "#################################################################"
	mkdir -p tests/site1/test && cd tests/site1/test && rm -rf * && \
	../../../nrx.py -c ../nrx.conf -i cyjs -f ../data/site1.cyjs -o clab -d && \
	for f in *; do echo Comparing file $$f ...; diff $$f ../data/$$f || exit 1; done
	@echo

test-site1-cyjs-2-clab-rename:
	@echo "#################################################################"
	@echo "# Site1: read from CYJS and export as Containerlab with a custom name"
	@echo "#################################################################"
	mkdir -p tests/site1/test && cd tests/site1/test && rm -rf * && \
	../../../nrx.py -c ../nrx.conf -i cyjs -f ../data/site1.cyjs -o clab --name ABC -d && \
	for f in *; do echo Comparing file $$f ...; diff $$f ../data/$$f || exit 1; done
	@echo

test-site1-cyjs-template-2-clab:
	@echo "#################################################################"
	@echo "# Site1: replace Platform in the template, read from CYJS and export as Containerlab"
	@echo "#################################################################"
	mkdir -p tests/site1/test && cd tests/site1/test && rm -rf * && \
	cat ../data/site1.cyjs.template | envsubst > site1.sonic-vs.cyjs && \
	../../../nrx.py -c ../nrx.conf -i cyjs -f site1.sonic-vs.cyjs -o clab -d && \
	for f in *.yaml; do echo Comparing file $$f ...; diff $$f ../data/$$f || exit 1; done
	@echo


test-h88-nb-2-cyjs-current:
	@echo "#################################################################"
	@echo "# h88: read from NetBox current version and export as CYJS"
	@echo "#################################################################"
	mkdir -p tests/h88/test && cd tests/h88/test && rm -rf * && \
	source ../../.env_current && \
	../../../nrx.py -c ../nrx.conf -o cyjs -d && \
	diff HQ.cyjs ../data/HQ.cyjs.current
	@echo

test-h88-nb-2-cyjs-latest:
	@echo "#################################################################"
	@echo "# h88: read from NetBox latest version and export as CYJS"
	@echo "#################################################################"
	mkdir -p tests/h88/test && cd tests/h88/test && rm -rf * && \
	source ../../.env_latest && \
	../../../nrx.py -c ../nrx.conf -o cyjs -d && \
	diff HQ.cyjs ../data/HQ.cyjs.latest
	@echo

test-h88-nb-2-cyjs-latest-noconfigs:
	@echo "#################################################################"
	@echo "# h88: read from NetBox latest version and export as CYJS with config export disabled"
	@echo "#################################################################"
	mkdir -p tests/h88/test && cd tests/h88/test && rm -rf * && \
	source ../../.env_latest && \
	../../../nrx.py -c ../nrx.conf -o cyjs -d --noconfigs && \
	diff HQ.cyjs ../data/HQ.cyjs.noconfigs
	@echo

test-h88-cyjs-2-clab:
	@echo "#################################################################"
	@echo "# h88: read from CYJS and export as Containerlab"
	@echo "#################################################################"
	mkdir -p tests/h88/test && cd tests/h88/test && rm -rf * && \
	../../../nrx.py -c ../nrx.conf -i cyjs -f ../data/HQ.cyjs -o clab -d && \
	for f in *; do echo Comparing file $$f ...; diff $$f ../data/$$f || exit 1; done
	@echo

update-h88:
	@echo "#################################################################"
	@echo "# Update reference data for h88"
	@echo "#################################################################"
	cd tests/h88/test && \
	cp * ../data/
	@echo

test-lrg-nb-2-cyjs-latest:
	@echo "#################################################################"
	@echo "# LRG: read from NetBox latest version and export as CYJS"
	@echo "#################################################################"
	mkdir -p tests/lrg/test && cd tests/lrg/test && rm -rf * && \
	source ../../.env_latest && \
	../../../nrx.py -c ../nrx.conf -o cyjs --noconfigs -d && \
	diff lrg.cyjs ../data/lrg.cyjs
	@echo

test-lrg-cyjs-2-graphite:
	@echo "#################################################################"
	@echo "# LRG: read from CYJS and export as graphite"
	@echo "#################################################################"
	mkdir -p tests/lrg/graphite && cd tests/lrg/graphite && rm -rf * && \
	../../../nrx.py -c ../nrx.conf -i cyjs -f ../data/lrg.cyjs -o graphite -d && \
	for f in *; do echo Comparing file $$f ...; diff $$f ../data/$$f || exit 1; done
	@echo

