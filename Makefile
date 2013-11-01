
all: pypy-c

PYPY_EXECUTABLE := $(shell which pypy)
URAM := $(shell python -c "import sys; print 4.5 if sys.maxint>1<<32 else 2.5")

ifeq ($(PYPY_EXECUTABLE),)
RUNINTERP = python
else
RUNINTERP = $(PYPY_EXECUTABLE)
endif

pypy-c:
	@echo
	@echo "============================================================="
ifeq ($(PYPY_EXECUTABLE),)
	@echo "Building a regular (jitting) version of PyPy, using CPython."
	@echo "This takes around 2 hours and $(URAM) GB of RAM."
	@echo "Note that pre-installing a PyPy binary would reduce this time"
	@echo "and produce basically the same result."
else
	@echo "Building a regular (jitting) version of PyPy, using"
	@echo "$(PYPY_EXECUTABLE) to run the translation itself."
	@echo "This takes around 45 minutes and $(URAM) GB of RAM."
endif
	@echo "============================================================="
	@echo
	@sleep 5
	$(RUNINTERP) rpython/bin/rpython -Ojit pypy/goal/targetpypystandalone.py
