==========================
What's new in PyPy2.7 5.4+
==========================

.. this is a revision shortly after release-pypy2.7-v5.4
.. startrev: 522736f816dc

.. branch: rpython-resync
Backport rpython changes made directly on the py3k and py3.5 branches.

.. branch: buffer-interface
Implement PyObject_GetBuffer, PyMemoryView_GET_BUFFER, and handles memoryviews
in numpypy

.. branch: force-virtual-state
Improve merging of virtual states in the JIT in order to avoid jumping to the
preamble. Accomplished by allocating virtual objects where non-virtuals are
expected.

.. branch: zarch-simd-support

s390x implementation for vector operations used in VecOpt

.. branch: ppc-vsx-support

PowerPC implementation for vector operations used in VecOpt
