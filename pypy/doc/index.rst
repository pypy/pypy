Welcome to PyPy's documentation!
================================

Welcome to the documentation for PyPy, a fast_, compliant alternative
implementation of the Python_ language.

* If you want to find out more about what PyPy is, have a look at our :doc:`introduction <introduction>`
  or consult the `PyPy website`_.

* If you're interested in trying PyPy out, check out the :doc:`installation instructions <install>`.

* If you want to help develop PyPy, please have a look at :doc:`how to contribute <how-to-contribute>`
  and get in touch (:ref:`contact`)!

All of the documentation and source code is available under the MIT license,
unless otherwise specified. Consult :source:`LICENSE`.

.. _fast: http://speed.pypy.org
.. _Python: http://python.org/
.. _PyPy website: http://pypy.org/


Getting Started
---------------

.. toctree::
   :maxdepth: 1

   introduction
   install
   build
   faq

Using PyPy
----------

.. toctree::
   :maxdepth: 1

   cpython_differences
   gc_info
   jit-hooks
   stackless
   cppyy
   objspace-proxies
   sandbox


Development documentation
-------------------------

.. toctree::
   :maxdepth: 1

   how-to-contribute
   project-ideas
   project-documentation
.. TODO: audit ^^


.. TODO: Fill this in


Academical stuff
----------------

.. toctree::
   :maxdepth: 1

   extradoc
.. TODO: Remove this? Or fill it with links to papers?


.. _contact:

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
