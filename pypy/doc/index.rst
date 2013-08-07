
Welcome to PyPy
===============

The PyPy project aims to produce a flexible and fast Python_
implementation.  This page documents the development of the PyPy
project itself. If you don't know what PyPy is, consult the `PyPy
website`_. If you just want to use PyPy, consult the `download`_ page
and the `getting started with pypy`_ documents. If you want to help
develop PyPy -- keep reading!

PyPy is written in a language called `RPython`_, which is suitable for
writing dynamic language interpreters (and not much else). RPython is
a subset of Python and is itself written in Python.  If you'd like to
learn more about RPython, `Starting with RPython`_ should provide a
reasonable overview.

**If you would like to contribute to PyPy**, please read `how to
contribute`_ first.  PyPy's development style is somewhat different to
that of many other software projects and it often surprises
newcomers. What is **not** necessary is an academic background from
university in writing compilers -- much of it does not apply to PyPy
any way.

All of the documentation and source code is available under the MIT license,
unless otherwise specified. Consult `LICENSE`_

.. _`download`: http://pypy.org/download.html
.. _`getting started with pypy`: getting-started-python.html
.. _`RPython`: coding-guide.html#RPython
.. _`Starting with RPython`: getting-started-dev.html
.. _`how to contribute`: how-to-contribute.html
.. _`PyPy website`: http://pypy.org
.. _`LICENSE`: https://bitbucket.org/pypy/pypy/src/default/LICENSE

Index of various topics:
========================

* `Getting started`_: how to install and run the PyPy Python interpreter

* `FAQ`_: some frequently asked questions.

* `Release 2.1.0`_: the latest official release

* `PyPy Blog`_: news and status info about PyPy 

* `Papers`_: Academic papers, talks, and related projects

* `speed.pypy.org`_: Daily benchmarks of how fast PyPy is

* `potential project ideas`_: In case you want to get your feet wet...

* `more stuff`_: this is a collection of documentation that's there, but not
  particularly organized 

Documentation for the PyPy Python Interpreter
=============================================

New features of PyPy's Python Interpreter and 
Translation Framework: 

  * `Differences between PyPy and CPython`_
  * `What PyPy can do for your objects`_ - transparent proxy documentation
  * `Continulets and greenlets`_ - documentation about stackless features
  * `JIT Generation in PyPy`_ 
  * `JIT hooks`_
  * `Sandboxing Python code`_
  * `Garbage collection environment variables`_

.. _`Differences between PyPy and CPython`: cpython_differences.html
.. _`What PyPy can do for your objects`: objspace-proxies.html
.. _`Continulets and greenlets`: stackless.html
.. _`JIT Generation in PyPy`: jit/index.html
.. _`JIT hooks`: jit-hooks.html
.. _`Sandboxing Python code`: sandbox.html
.. _`Garbage collection environment variables`: gc_info.html

Mailing lists, bug tracker, IRC channel
=============================================

* `Development mailing list`_: development and conceptual
  discussions. 

* `Mercurial commit mailing list`_: updates to code and
  documentation. 

* `Development bug/feature tracker`_: filing bugs and feature requests. 

* **IRC channel #pypy on freenode**: Many of the core developers are hanging out 
  at #pypy on irc.freenode.net.  You are welcome to join and ask questions
  (if they are not already developed in the FAQ_).
  You can find logs of the channel here_.

Meeting PyPy developers
=======================

The PyPy developers are organizing sprints and presenting results at
conferences all year round. They will be happy to meet in person with
anyone interested in the project.  Watch out for sprint announcements
on the `development mailing list`_.

.. _Python: http://docs.python.org/index.html
.. _`more...`: architecture.html#mission-statement 
.. _`PyPy blog`: http://morepypy.blogspot.com/
.. _`development bug/feature tracker`: https://bugs.pypy.org
.. _here: http://tismerysoft.de/pypy/irc-logs/pypy
.. _`Mercurial commit mailing list`: http://python.org/mailman/listinfo/pypy-commit
.. _`development mailing list`: http://python.org/mailman/listinfo/pypy-dev
.. _`FAQ`: faq.html
.. _`Getting Started`: getting-started.html
.. _`Papers`: extradoc.html
.. _`Videos`: video-index.html
.. _`Release 2.1.0`: http://pypy.org/download.html
.. _`speed.pypy.org`: http://speed.pypy.org
.. _`RPython toolchain`: translation.html
.. _`potential project ideas`: project-ideas.html
.. _`more stuff`: project-documentation.html

.. include:: _ref.txt
