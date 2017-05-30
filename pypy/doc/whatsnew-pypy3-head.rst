=========================
What's new in PyPy3 5.8+
=========================

.. this is the revision after release-pypy3.3-5.8.x was branched
.. startrev: 0f08064cf67c

.. branch: mtest
Use "<python> -m test" to run the CPython test suite, as documented by CPython,
instead of our outdated regrverbose.py script.

.. branch: win32-faulthandler

Enable the 'faulthandler' module on Windows;
this unblocks the Python test suite.

.. branch: superjumbo

Implement posix.posix_fallocate() and posix.posix_fadvise()

.. branch: py3.5-mac-translate

Fix for different posix primitives on MacOS

.. branch: PyBuffer

Internal refactoring of memoryviews and buffers, fixing some related
performance issues.
