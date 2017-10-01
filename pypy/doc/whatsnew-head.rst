===========================
What's new in PyPy2.7 5.10+
===========================

.. this is a revision shortly after release-pypy2.7-v5.9.0
.. startrev:899e5245de1e

.. branch: cpyext-jit

Differentiate the code to call METH_NOARGS, METH_O and METH_VARARGS in cpyext:
this allows to write specialized code which is much faster than previous
completely generic version. Moreover, let the JIT to look inside the cpyext
module: the net result is that cpyext calls are up to 7x faster. However, this
is true only for very simple situations: in all real life code, we are still
much slower than CPython (more optimizations to come)
