======================
What's new in PyPy 1.9
======================

.. this is the revision just after the creation of the release-1.8.x branch
.. startrev: a4261375b359

.. branch: array_equal
.. branch: better-jit-hooks-2
.. branch: exception-cannot-occur
.. branch: faster-heapcache
.. branch: faster-str-decode-escape
.. branch: float-bytes
.. branch: float-bytes-2
.. branch: jit-frame-counter
.. branch: kill-geninterp
.. branch: kqueue
.. branch: kwargsdict-strategy
.. branch: matrixmath-dot
numpypy can now handle matrix multiplication.
.. branch: merge-2.7.2
The stdlib was updated to version 2.7.2
.. branch: ndmin
.. branch: newindex
.. branch: non-null-threadstate
.. branch: numppy-flatitter
.. branch: numpy-back-to-applevel
.. branch: numpy-concatenate
.. branch: numpy-indexing-by-arrays-bool
.. branch: numpy-record-dtypes
.. branch: numpy-single-jitdriver
.. branch: numpy-ufuncs2
.. branch: numpy-ufuncs3
.. branch: numpypy-issue1137
.. branch: numpypy-out
The "out" argument was added to most of the numypypy functions.
.. branch: numpypy-shape-bug
.. branch: numpypy-ufuncs
.. branch: pytest
.. branch: revive-dlltool
.. branch: safe-getargs-freelist
.. branch: set-strategies
.. branch: speedup-list-comprehension
.. branch: stdlib-unification
.. branch: step-one-xrange
.. branch: string-NUL
.. branch: win32-cleanup
.. branch: win32-cleanup2
.. branch: win32-cleanup_2
Many bugs were corrected for windows 32 bit. New functionality was added to
test validity of file descriptors, leading to the removal of the  global 
_invalid_parameter_handler
.. branch: win64-stage1
.. branch: zlib-mem-pressure


.. "uninteresting" branches that we should just ignore for the whatsnew:
.. branch: sanitize-finally-stack
