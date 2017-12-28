===========================
What's new in PyPy2.7 5.10+
===========================

.. this is a revision shortly after release-pypy2.7-v5.10.0
.. startrev: 6b024edd9d12

.. branch: cpyext-avoid-roundtrip

Big refactoring of some cpyext code, which avoids a lot of nonsense when
calling C from Python and vice-versa: the result is a big speedup in
function/method calls, up to 6 times faster.
