============================
What's new in PyPy2.7 7.3.1+
============================

.. this is a revision shortly after release-pypy-7.3.1
.. startrev: 1cae9900d598

.. branch: optimize-sre-unicode

Speed up performance of matching Unicode strings in the ``re`` module
significantly for characters that are part of ASCII.

.. branch: rpython-recvmsg_into

Refactor RSocket.xxx_into() methods and add .recvmsg_into().

.. branch: bo-fix-source-links

Fix documentation extlinks for heptapod directory schema

.. branch: py3.6 # ignore, bad merge

.. branch: ssl  # ignore, small test fix

.. branch: ctypes-stuff

Fix implementation of PEP 3118 in ctypes.
