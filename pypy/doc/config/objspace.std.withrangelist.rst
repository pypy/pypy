Enable "range list" objects. They are an additional implementation of the Python
``list`` type, indistinguishable for the normal user. Whenever the ``range``
builtin is called, an range list is returned. As long as this list is not
mutated (and for example only iterated over), it uses only enough memory to
store the start, stop and step of the range. This makes using ``range`` as
efficient as ``xrange``, as long as the result is only used in a ``for``-loop.

See the section in `Standard Interpreter Optimizations`_ for more details.

.. _`Standard Interpreter Optimizations`: ../interpreter-optimizations.html#range-lists

