==========================
What's new in PyPy2.7 6.0+
==========================

.. this is a revision shortly after release-pypy-6.0.0
.. startrev: e50e11af23f1

.. branch: cppyy-packaging

Upgrade to backend 0.6.0, support exception handling from wrapped functions,
update enum handling, const correctness for data members and associated tests,
support anonymous enums, support for function pointer arguments

.. branch: socket_default_timeout_blockingness

Make sure 'blocking-ness' of socket is set along with default timeout

.. branch: crypt_h

Include crypt.h for crypt() on Linux

.. branch: gc-more-logging

Log additional gc-minor and gc-collect-step info in the PYPYLOG

.. branch: reverse-debugger

The reverse-debugger branch has been merged.  For more information, see
https://bitbucket.org/pypy/revdb

.. branch: unicode-utf8-re
.. branch: utf8-io

Utf8 handling for unicode


