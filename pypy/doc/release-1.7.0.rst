=====================
PyPy 1.7
=====================

Highlights
==========

* numerous performance improvements, PyPy 1.7 is xxx faster than 1.6

* numerous bugfixes, compatibility fixes

* windows fixes

* stackless and JIT integration
  (stackless is now in the same executable, but any loop using
  stackless features will interrupt the JIT for now, so no real
  performance improvement for now)

* numpy progress - dtypes, numpy -> numpypy renaming

* brand new, faster, JSON encoder

* improved memory footprint on some RPython modules, such as hashlib

* cpyext progress

Things that didn't make it, expect in 1.8 soon
==============================================

* list strategies

* multi-dimensional arrays for numpy

* ARM backend

* PPC backend

Things we're working on with unclear ETA
========================================

* windows 64 (?)

* Py3k

* SSE for numpy

* specialized objects
