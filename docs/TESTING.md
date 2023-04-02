```Shell
source nrx39-dev/bin/activate
pip install -r requirements-dev.txt
```

```Shell
cd tests/dc1/test
../../../nrx.py -c ../nrx.conf -i cyjs -f ../data/dc1.cyjs -d
for f in *; do diff $f ../data/$f; done
```