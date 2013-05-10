Welcome to PyPy
===============

The PyPy project aims to produce a flexible and fast Python_
implementation.  This page documents the development of the PyPy
project itself. If you don't know what PyPy is, consult the `PyPy
website`_. If you just want to use PyPy, consult the `download`_ page
and the :doc:`getting-started-python` documents. If you want to help
develop PyPy -- keep reading!

PyPy is written in a language called `RPython`_, which is suitable for
writing dynamic language interpreters (and not much else). RPython is
a subset of Python and is itself written in Python.  If you'd like to
learn more about RPython, `XXXX` should provide a
reasonable overview.

**If you would like to contribute to PyPy**, please read :doc:`how to
contribute <how-to-contribute>` first.  PyPy's development style is somewhat different to
that of many other software projects and it often surprises
newcomers. What is **not** necessary is an academic background from
university in writing compilers -- much of it does not apply to PyPy
any way.

All of the documentation and source code is available under the MIT license,
unless otherwise specified. Consult :source:`LICENSE`.

.. _Python: http://python.org/
.. _download: http://pypy.org/download.html
.. _PyPy website: http://pypy.org/
.. _RPython: http://rpython.readthedocs.org/

.. toctree::
   :hidden:

   getting-started-python
   how-to-contribute


Index of various topics:
------------------------

* :doc:`getting-started`: how to install and run the PyPy Python interpreter

* :doc:`FAQ <faq>`: some frequently asked questions.

* `Release 2.0 beta 2`_: the latest official release

* `PyPy Blog`_: news and status info about PyPy

* :doc:`Papers <extradoc>`: Academic papers, talks, and related projects

* `speed.pypy.org`_: Daily benchmarks of how fast PyPy is

* :doc:`project-ideas`: In case you want to get your feet wet...

* :doc:`More stuff <project-documentation>`: this is a collection of documentation that's there, but not
  particularly organized

.. _PyPy blog: http://morepypy.blogspot.com/
.. _Release 2.0 beta 2: http://pypy.org/download.html
.. _speed.pypy.org: http://speed.pypy.org

.. toctree::
   :hidden:

   getting-started
   faq
   extradoc
   project-ideas
   project-documentation


Documentation for the PyPy Python Interpreter
---------------------------------------------

New features of PyPy's Python Interpreter and
Translation Framework:

  * :doc:`cpython_differences`
  * :doc:`objspace-proxies` - transparent proxy documentation
  * :doc:`Continulets and greenlets <stackless>` - documentation about stackless features
  * :doc:`jit-hooks`
  * :doc:`sandbox`
  * :doc:`Garbage collection environment variables <gc_info>`

.. toctree::
   :hidden:

   cpython_differences
   objspace-proxies
   stackless
   jit-hooks
   sandbox
   gc_info


.. _contact:

Mailing lists, bug tracker, IRC channel
---------------------------------------------

* `Development mailing list`_: development and conceptual
  discussions.

* `Mercurial commit mailing list`_: updates to code and
  documentation.

* `Development bug/feature tracker`_: filing bugs and feature requests.

* **IRC channel #pypy on freenode**: Many of the core developers are hanging out
  at #pypy on irc.freenode.net.  You are welcome to join and ask questions
  (if they are not already developed in the :doc:`FAQ <faq>`).
  You can find logs of the channel here_.

.. _development mailing list: http://python.org/mailman/listinfo/pypy-dev
.. _Mercurial commit mailing list: http://python.org/mailman/listinfo/pypy-commit
.. _development bug/feature tracker: https://bugs.pypy.org
.. _here: http://tismerysoft.de/pypy/irc-logs/pypy


Meeting PyPy developers
-----------------------

The PyPy developers are organizing sprints and presenting results at
conferences all year round. They will be happy to meet in person with
anyone interested in the project.  Watch out for sprint announcements
on the `development mailing list`_.
