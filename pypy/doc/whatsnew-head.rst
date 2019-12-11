============================
What's new in PyPy2.7 7.3.0+
============================

.. this is a revision shortly after release-pypy-7.3.0
.. startrev: dbbbae99135f 

.. branch: backport-decode_timeval_ns-py3.7

Backport ``rtime.decode_timeval_ns`` from py3.7 to rpython

.. branch: kill-asmgcc

Completely remove the deprecated translation option ``--gcrootfinder=asmgcc``
because it no longer works with a recent enough ``gcc``.
