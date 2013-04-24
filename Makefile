
all: pypy-c

pypy-c:
	@echo "Building PyPy with JIT, it'll take about 40 minutes and 4G of RAM"
	@sleep 3
	rpython/bin/rpython -Ojit pypy/goal/targetpypystandalone.py
