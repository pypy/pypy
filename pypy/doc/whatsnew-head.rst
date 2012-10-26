======================
What's new in PyPy xxx
======================

.. this is the revision of the last merge from default to release-1.9.x
.. startrev: 8d567513d04d

.. branch: default
.. branch: app_main-refactor
.. branch: win-ordinal
.. branch: reflex-support
Provides cppyy module (disabled by default) for access to C++ through Reflex.
See doc/cppyy.rst for full details and functionality.
.. branch: nupypy-axis-arg-check
Check that axis arg is valid in _numpypy

.. branch: iterator-in-rpython
.. branch: numpypy_count_nonzero
.. branch: numpy-refactor
Remove numpy lazy evaluation and simplify everything
.. branch: numpy-reintroduce-jit-drivers
.. branch: numpy-fancy-indexing
Support for array[array-of-ints] in numpy
.. branch: even-more-jit-hooks
Implement better JIT hooks
.. branch: virtual-arguments
Improve handling of **kwds greatly, making them virtual sometimes.
.. branch: improve-rbigint
Introduce __int128 on systems where it's supported and improve the speed of
rlib/rbigint.py greatly.
.. branch: translation-cleanup
Start to clean up a bit the flow object space.
.. branch: ffi-backend
Support CFFI.  http://morepypy.blogspot.ch/2012/08/cffi-release-03.html
.. branch: speedup-unpackiterable
.. branch: stdlib-2.7.3
The stdlib was updated to version 2.7.3

.. branch: numpypy-complex2
Complex dtype support for numpy
.. branch: kill-someobject
major cleanups including killing some object support


.. "uninteresting" branches that we should just ignore for the whatsnew:
.. branch: slightly-shorter-c
.. branch: better-enforceargs
.. branch: rpython-unicode-formatting
.. branch: jit-opaque-licm
.. branch: rpython-utf8
Support for utf-8 encoding in RPython
.. branch: arm-backend-2
Support ARM in the JIT.
