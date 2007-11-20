Determine which `Object Space`_ to use. The `Standard Object Space`_ gives the
normal Python semantics, the others are `Object Space Proxies`_ giving
additional features (except the Flow Object Space which is not intended
for normal usage):

  * thunk_: The thunk object space adds lazy evaluation to PyPy.
  * taint_: The taint object space adds soft security features.
  * dump_:  Using this object spaces results in the dumpimp of all operations
    to a log.

.. _`Object Space`: ../objspace.html
.. _`Object Space Proxies`: ../objspace-proxies.html
.. _`Standard Object Space`: ../objspace.html#standard-object-space
.. _thunk: ../objspace-proxies.html#thunk
.. _taint: ../objspace-proxies.html#taint
.. _dump: ../objspace-proxies.html#dump
