Welcome to PyPy's documentation!
================================

Welcome to the documentation for PyPy, a fast_, compliant alternative
implementation of the Python_ language. If you don't know what PyPy is,
consult the `PyPy website`_.

PyPy is written using the RPython toolchain. RPython enables writing dynamic
language interpreters in a subset of Python which can be translated to C code
including an automatically generated JIT for the implemented language. If you
want to learn more about RPython, see the `RPython website`_.

.. _fast: http://speed.pypy.org
.. _Python: http://python.org/
.. _PyPy website: http://pypy.org/
.. _RPython website: http://rpython.readthedocs.org/


User documentation
------------------

.. toctree::
   :maxdepth: 1

   install
   build
   cpython_differences
   gc_info
   jit-hooks
   stackless
   cppyy
   objspace-proxies
   sandbox
   clr-module


Development documentation
-------------------------

.. toctree::
   :maxdepth: 2


Academical stuff
----------------

.. toctree::
   :maxdepth: 2


Contact
-------

`#pypy on irc.freenode.net`_
    Many of the core developers are hanging out here. You are welcome to join
    and ask questions (if they are not already answered in the :doc:`FAQ
    <faq>`). You can find logs of the channel here_.

`Development mailing list`_
    Development and conceptual discussions

`Commit mailing list`_
    Updates to code and documentation

`Development bug/feature tracker`_
    Filing bugs and feature requests

Meeting PyPy developers
    The PyPy developers are organizing sprints and presenting results at
    conferences all year round. They will be happy to meet in person with
    anyone interested in the project. Watch out for sprint announcements on
    the `development mailing list`_.

.. _#pypy on irc.freenode.net: irc://irc.freenode.net/pypy
.. _here: http://tismerysoft.de/pypy/irc-logs/pypy
.. _Development mailing list: http://python.org/mailman/listinfo/pypy-dev
.. _Commit mailing list: http://python.org/mailman/listinfo/pypy-commit
.. _Development bug/feature tracker: https://bugs.pypy.org/


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

