lint:
	pylint nrx/*.py

test-local: test-dc1 test-dc2
test: test-dc1-cyjs-2-clab test-dc2-cyjs-2-cml

test-dc1: test-dc1-nb-2-cyjs test-dc1-cyjs-2-clab
test-dc2: test-dc2-nb-2-cyjs test-dc2-cyjs-2-cml

test-dc1-nb-2-cyjs:
	@echo "#################################################################"
	@echo "# DC1: read from NetBox and export as CYJS"
	@echo "#################################################################"
	mkdir -p tests/dc1/test && cd tests/dc1/test && rm -f * && \
	source ../.env && \
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

test-dc2-nb-2-cyjs:
	@echo "#################################################################"
	@echo "# DC2: read from NetBox and export as CYJS"
	@echo "#################################################################"
	mkdir -p tests/dc2/test && cd tests/dc2/test && rm -f * && \
	source ../.env && \
	../../../nrx.py -c ../nrx.conf -o cyjs -d && \
	diff dc2.cyjs ../data/dc2.cyjs
	@echo

test-dc2-cyjs-2-cml:
	@echo "#################################################################"
	@echo "# DC2: read from CYJS and export as CML"
	@echo "#################################################################"
	mkdir -p tests/dc2/test && cd tests/dc2/test && rm -f * && \
	../../../nrx.py -c ../nrx.conf -i cyjs -f ../data/dc2.cyjs -d && \
	for f in *; do echo Comparing file $$f ...; diff $$f ../data/$$f || exit 1; done
	@echo
