test: test-dc1

test-dc1: test-dc1-cyjs-2-clab

test-dc1-cyjs-2-clab:
	@echo "#################################################################"
	@echo "# DC1: read from CYJS and export as Containerlab"
	@echo "#################################################################"
	cd tests/dc1/test && rm * && \
	../../../nrx.py -c ../nrx.conf -i cyjs -f ../data/dc1.cyjs -d && \
	for f in *; do diff $$f ../data/$$f; done
	@echo
