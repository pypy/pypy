=======================
What's new in PyPy 2.5+
=======================

.. this is a revision shortly after release-2.5.x
.. startrev: 397b96217b85


Non-blocking file reads sometimes raised EAGAIN even though they
had buffered data waiting, fixed in b1c4fcb04a42


.. branch: vmprof

.. branch: stackroot-speedup-2
Avoid tracing all stack roots during repeated minor collections,
by ignoring the part of the stack that didn't change

.. branch: stdlib-2.7.9
Update stdlib to version 2.7.9

.. branch: fix-kqueue-error2
Fix exception being raised by kqueue.control (CPython compatibility)

.. branch: gitignore
