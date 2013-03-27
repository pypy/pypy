
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

Index of various topics:
========================

* `Getting started`_: how to install and run the PyPy Python interpreter

* `FAQ`_: some frequently asked questions.

* `Release 2.0 beta 1`_: the latest official release

* `PyPy Blog`_: news and status info about PyPy 

* `Papers`_: Academic papers, talks, and related projects

* `speed.pypy.org`_: Daily benchmarks of how fast PyPy is

* `potential project ideas`_: In case you want to get your feet wet...

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

Status_ of the project.

.. _`Differences between PyPy and CPython`: cpython_differences.html
.. _`What PyPy can do for your objects`: objspace-proxies.html
.. _`Continulets and greenlets_`: stackless.html
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
.. _`Release 2.0 beta 1`: http://pypy.org/download.html
.. _`speed.pypy.org`: http://speed.pypy.org
.. _`RPython toolchain`: translation.html
.. _`potential project ideas`: project-ideas.html

Project Documentation
=====================================

`architecture`_ gives a complete view of PyPy's basic design. 

`coding guide`_ helps you to write code for PyPy (especially also describes
coding in RPython a bit). 

`sprint reports`_ lists reports written at most of our sprints, from
2003 to the present.

`papers, talks and related projects`_ lists presentations 
and related projects as well as our published papers.

`PyPy video documentation`_ is a page linking to the videos (e.g. of talks and
introductions) that are available.

`Technical reports`_ is a page that contains links to the
reports that we submitted to the European Union.

`development methodology`_ describes our sprint-driven approach.

`LICENSE`_ contains licensing details (basically a straight MIT-license). 

`Glossary`_ of PyPy words to help you align your inner self with
the PyPy universe.

Status
===================================

PyPy can be used to run Python programs on Linux, OS/X,
Windows.
To dig into PyPy it is recommended to try out the current
Mercurial default branch, which is always working or mostly working,
instead of the latest release, which is `2.0 beta1`__.

.. __: release-2.0.0-beta1.html

PyPy is mainly developed on Linux and Mac OS X.  Windows is supported,
but platform-specific bugs tend to take longer before we notice and fix
them.  Linux 64-bit machines are supported (though it may also take some
time before we notice and fix bugs).

PyPy's own tests `summary`_, daily updated, run through BuildBot infrastructure.
You can also find CPython's compliance tests run with compiled ``pypy-c``
executables there.


Source Code Documentation
===============================================

`object spaces`_ discusses the object space interface 
and several implementations. 

`bytecode interpreter`_ explains the basic mechanisms 
of the bytecode interpreter and virtual machine. 

`interpreter optimizations`_ describes our various strategies for
improving the performance of our interpreter, including alternative
object implementations (for strings, dictionaries and lists) in the
standard object space.

`translation`_ is a detailed overview of our translation process.  The
rtyper_ is the largest component of our translation process.

`dynamic-language translation`_ is a paper that describes
the translation process, especially the flow object space
and the annotator in detail. (This document is one
of the `EU reports`_.)

`low-level encapsulation`_ describes how our approach hides
away a lot of low level details. This document is also part
of the `EU reports`_.

`translation aspects`_ describes how we weave different
properties into our interpreter during the translation
process. This document is also part of the `EU reports`_.

`garbage collector`_ strategies that can be used by the virtual
machines produced by the translation process.

`parser`_ contains (outdated, unfinished) documentation about
the parser.

`rlib`_ describes some modules that can be used when implementing programs in
RPython.

`configuration documentation`_ describes the various configuration options that
allow you to customize PyPy.

`pypy on windows`_

`command line reference`_

`CLI backend`_ describes the details of the .NET backend.

`JIT Generation in PyPy`_ describes how we produce the Python Just-in-time Compiler
from our Python interpreter.

`directory cross-reference`_

.. _`garbage collector`: garbage_collection.html
.. _`directory cross-reference`: dir-reference.html
.. _`pypy on windows`: windows.html
.. _`command line reference`: commandline_ref.html
.. _`FAQ`: faq.html
.. _Glossary: glossary.html
.. _`PyPy video documentation`: video-index.html
.. _parser: parser.html
.. _`development methodology`: dev_method.html
.. _`sprint reports`: sprint-reports.html
.. _`papers, talks and related projects`: extradoc.html
.. _`object spaces`: objspace.html 
.. _`interpreter optimizations`: interpreter-optimizations.html 
.. _`translation`: translation.html 
.. _`dynamic-language translation`: https://bitbucket.org/pypy/extradoc/raw/tip/eu-report/D05.1_Publish_on_translating_a_very-high-level_description.pdf
.. _`low-level encapsulation`: low-level-encapsulation.html
.. _`translation aspects`: translation-aspects.html
.. _`configuration documentation`: config/
.. _`coding guide`: coding-guide.html 
.. _`Architecture`: architecture.html 
.. _`getting started`: getting-started.html 
.. _`bytecode interpreter`: interpreter.html 
.. _`EU reports`: index-report.html
.. _`Technical reports`: index-report.html
.. _`summary`: http://buildbot.pypy.org/summary
.. _`ideas for PyPy related projects`: project-ideas.html
.. _`Nightly builds and benchmarks`: http://tuatara.cs.uni-duesseldorf.de/benchmark.html
.. _`directory reference`: 
.. _`rlib`: rlib.html
.. _`Sandboxing Python code`: sandbox.html
.. _`LICENSE`: https://bitbucket.org/pypy/pypy/src/default/LICENSE

.. The following documentation is important and reasonably up-to-date:

.. extradoc: should this be integrated one level up: dcolish?

.. toctree::
   :maxdepth: 1
   :hidden:

   interpreter.rst
   objspace.rst
   __pypy__-module.rst
   objspace-proxies.rst
   config/index.rst

   dev_method.rst
   extending.rst

   extradoc.rst
   video-index.rst

   glossary.rst

   contributor.rst

   interpreter-optimizations.rst
   configuration.rst
   parser.rst
   rlib.rst
   rtyper.rst
   rffi.rst
   
   translation.rst
   jit/index.rst
   jit/overview.rst
   jit/pyjitpl5.rst

   index-of-release-notes.rst

   ctypes-implementation.rst

   how-to-release.rst

   index-report.rst

   stackless.rst
   sandbox.rst

   discussions.rst

   cleanup.rst

   sprint-reports.rst

   eventhistory.rst
   statistic/index.rst

Indices and tables
==================

* :ref:`genindex`
* :ref:`search`
* :ref:`glossary`


.. include:: _ref.txt
