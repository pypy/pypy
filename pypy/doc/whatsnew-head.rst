======================
What's new in PyPy 2.1
======================

.. this is a revision shortly after release-2.0
.. startrev: a13c07067613

.. branch: numpy-pickle
Pickling of numpy arrays and dtypes (including record dtypes)

.. branch: remove-array-smm
Remove multimethods in the arraymodule

.. branch: callback-stacklet
Fixed bug when switching stacklets from a C callback

.. branch: remove-set-smm
Remove multi-methods on sets

.. branch: numpy-subarrays
Implement subarrays for numpy

.. branch: remove-dict-smm
Remove multi-methods on dict

.. branch: remove-list-smm-2
Remove remaining multi-methods on list

.. branch: arm-stacklet
Stacklet support for ARM, enables _continuation support

.. branch: remove-tuple-smm
Remove multi-methods on tuple

.. branch: remove-iter-smm
Remove multi-methods on iterators

.. branch: emit-call-x86
.. branch: emit-call-arm

.. branch: on-abort-resops
Added list of resops to the pypyjit on_abort hook.

.. branch: logging-perf
Speeds up the stdlib logging module

.. branch: operrfmt-NT
Adds a couple convenient format specifiers to operationerrfmt

.. branch: win32-fixes3
Skip and fix some non-translated (own) tests for win32 builds

.. branch: ctypes-byref
Add the '_obj' attribute on ctypes pointer() and byref() objects

.. branch: argsort-segfault
Fix a segfault in argsort when sorting by chunks on multidim numpypy arrays (mikefc)

.. branch: dtype-isnative
.. branch: ndarray-round

.. branch: faster-str-of-bigint
Improve performance of str(long).
