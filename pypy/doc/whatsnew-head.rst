===========================
What's new in PyPy2.7 5.10+
===========================

.. this is a revision shortly after release-pypy2.7-v5.10.0
.. startrev: 6b024edd9d12

.. branch: cpyext-avoid-roundtrip

Big refactoring of some cpyext code, which avoids a lot of nonsense when
calling C from Python and vice-versa: the result is a big speedup in
function/method calls, up to 6 times faster.

.. branch: cpyext-datetime2

Support ``tzinfo`` field on C-API datetime objects, fixes latest pandas HEAD


.. branch: mapdict-size-limit

Fix a corner case of mapdict: When an instance is used like a dict (using
``setattr`` and ``getattr``, or ``.__dict__``) and a lot of attributes are
added, then the performance using mapdict is linear in the number of
attributes. This is now fixed (by switching to a regular dict after 80
attributes).


.. branch: cpyext-faster-arg-passing

When using cpyext, improve the speed of passing certain objects from PyPy to C
code, most notably None, True, False, types, all instances of C-defined types.
Before, a dict lookup was needed every time such an object crossed over, now it
is just a field read.
