```Shell
cd tests/dc1/test
../../../nrx.py -c ../nrx.conf -i cyjs -f ../data/dc1.cyjs -d
for f in *; do diff $f ../data/$f; done
```