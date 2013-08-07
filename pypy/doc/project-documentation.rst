
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
