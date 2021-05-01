============================
What's new in PyPy2.7 7.3.4+
============================

.. this is a revision shortly after release-pypy-7.3.4
.. startrev: 9c11d242d78c


.. branch: faster-rbigint-big-divmod

Speed up ``divmod`` for very large numbers. This also speeds up string
formatting of big numbers.

.. branch: jit-heapcache-interiorfields

Optimize dictionary operations in the JIT a bit more, making it possible to
completely optimize away the creation of dictionaries in more situations (such
as calling the ``dict.update`` method on known dicts).


.. branch: jit-instance-ptr-eq-improvements

Make the JIT reason better about ``a is b``, specifically the
``instance_ptr_eq`` and ``ptr_eq`` operations: if they are followed by a
``guard_true``, we can replace ``b`` with ``a`` in the rest of the trace.
