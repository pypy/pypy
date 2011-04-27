=================================================
PyPy - a Python_ implementation written in Python 
=================================================

.. _Python: http://docs.python.org/release/2.5.2/


.. contents:: :depth: 1


PyPy User Documentation
===============================================

`getting started`_ provides hands-on instructions 
including a two-liner to run the PyPy Python interpreter 
on your system, examples on advanced features and 
entry points for using PyPy's translation tool chain. 

`FAQ`_ contains some frequently asked questions.

New features of PyPy's Python Interpreter and 
Translation Framework: 

  * `Differences between PyPy and CPython`_
  * `What PyPy can do for your objects`_
  * `Stackless and coroutines`_
  * `JIT Generation in PyPy`_ 
  * `Sandboxing Python code`_

Status_ of the project.


Project Documentation
=====================================

PyPy was funded by the EU for several years. See the `web site of the EU
project`_ for more details.

.. _`web site of the EU project`: http://pypy.org

architecture_ gives a complete view of PyPy's basic design. 

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
Windows, on top of .NET, and on top of Java.
To dig into PyPy it is recommended to try out the current
Subversion HEAD, which is always working or mostly working,
instead of the latest release, which is `1.2.0`__.

.. __: release-1.2.0.html

PyPy is mainly developed on Linux and Mac OS X.  Windows is supported,
but platform-specific bugs tend to take longer before we notice and fix
them.  Linux 64-bit machines are supported (though it may also take some
time before we notice and fix bugs).

PyPy's own tests `summary`_, daily updated, run through BuildBot infrastructure.
You can also find CPython's compliance tests run with compiled ``pypy-c``
executables there.

information dating from early 2007: 

`PyPy LOC statistics`_ shows LOC statistics about PyPy.

`PyPy statistics`_ is a page with various statistics about the PyPy project.

`compatibility matrix`_ is a diagram that shows which of the various features
of the PyPy interpreter work together with which other features.


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

`CLI backend`_ describes the details of the .NET backend.

`JIT Generation in PyPy`_ describes how we produce the Python Just-in-time Compiler
from our Python interpreter.



.. _`FAQ`: faq.html
.. _Glossary: glossary.html
.. _`PyPy video documentation`: video-index.html
.. _parser: parser.html
.. _`development methodology`: dev_method.html
.. _`sprint reports`: sprint-reports.html
.. _`papers, talks and related projects`: extradoc.html
.. _`PyPy LOC statistics`: http://codespeak.net/~hpk/pypy-stat/
.. _`PyPy statistics`: http://codespeak.net/pypy/trunk/pypy/doc/statistic
.. _`object spaces`: objspace.html 
.. _`interpreter optimizations`: interpreter-optimizations.html 
.. _`translation`: translation.html 
.. _`dynamic-language translation`: https://bitbucket.org/pypy/extradoc/raw/tip/eu-report/D05.1_Publish_on_translating_a_very-high-level_description.pdf
.. _`low-level encapsulation`: low-level-encapsulation.html
.. _`translation aspects`: translation-aspects.html
.. _`configuration documentation`: config/
.. _`coding guide`: coding-guide.html 
.. _`architecture`: architecture.html 
.. _`getting started`: getting-started.html 
.. _`bytecode interpreter`: interpreter.html 
.. _`EU reports`: index-report.html
.. _`Technical reports`: index-report.html
.. _`summary`: http://codespeak.net:8099/summary
.. _`ideas for PyPy related projects`: project-ideas.html
.. _`Nightly builds and benchmarks`: http://tuatara.cs.uni-duesseldorf.de/benchmark.html
.. _`directory reference`: 
.. _`rlib`: rlib.html
.. _`Sandboxing Python code`: sandbox.html
.. _`LICENSE`: https://bitbucket.org/pypy/pypy/src/default/LICENSE

PyPy directory cross-reference 
------------------------------

Here is a fully referenced alphabetical two-level deep 
directory overview of PyPy: 

================================   =========================================== 
Directory                          explanation/links
================================   =========================================== 
`pypy/annotation/`_                `type inferencing code`_ for `RPython`_ programs 

`pypy/bin/`_                       command-line scripts, mainly `py.py`_ and `translatorshell.py`_

`pypy/config/`_                    handles the numerous options for building and running PyPy

`pypy/doc/`_                       text versions of PyPy developer documentation

`pypy/doc/config/`_                documentation for the numerous translation options

`pypy/doc/discussion/`_            drafts of ideas and documentation

``doc/*/``                         other specific documentation topics or tools

`pypy/interpreter/`_               `bytecode interpreter`_ and related objects
                                   (frames, functions, modules,...) 

`pypy/interpreter/pyparser/`_      interpreter-level Python source parser

`pypy/interpreter/astcompiler/`_   interpreter-level bytecode compiler, via an AST
                                   representation

`pypy/module/`_                    contains `mixed modules`_ implementing core modules with 
                                   both application and interpreter level code.
                                   Not all are finished and working.  Use the ``--withmod-xxx``
                                   or ``--allworkingmodules`` translation options.

`pypy/objspace/`_                  `object space`_ implementations

`pypy/objspace/trace.py`_          the `trace object space`_ monitoring bytecode and space operations

`pypy/objspace/dump.py`_           the dump object space saves a large, searchable log file
                                   with all operations

`pypy/objspace/taint.py`_          the `taint object space`_, providing object tainting

`pypy/objspace/thunk.py`_          the `thunk object space`_, providing unique object features 

`pypy/objspace/flow/`_             the FlowObjSpace_ implementing `abstract interpretation`_

`pypy/objspace/std/`_              the StdObjSpace_ implementing CPython's objects and types

`pypy/rlib/`_                      a `"standard library"`_ for RPython_ programs

`pypy/rpython/`_                   the `RPython Typer`_ 

`pypy/rpython/lltypesystem/`_      the `low-level type system`_ for C-like backends

`pypy/rpython/ootypesystem/`_      the `object-oriented type system`_ for OO backends

`pypy/rpython/memory/`_            the `garbage collector`_ construction framework

`pypy/tool/`_                      various utilities and hacks used from various places 

`pypy/tool/algo/`_                 general-purpose algorithmic and mathematic
                                   tools

`pypy/tool/pytest/`_               support code for our `testing methods`_

`pypy/translator/`_                translation_ backends and support code

`pypy/translator/backendopt/`_     general optimizations that run before a backend generates code

`pypy/translator/c/`_              the `GenC backend`_, producing C code from an
                                   RPython program (generally via the rtyper_)

`pypy/translator/cli/`_            the `CLI backend`_ for `.NET`_ (Microsoft CLR or Mono_)

`pypy/translator/goal/`_           our `main PyPy-translation scripts`_ live here

`pypy/translator/jvm/`_            the Java backend

`pypy/translator/stackless/`_      the `Stackless Transform`_

`pypy/translator/tool/`_           helper tools for translation, including the Pygame
                                   `graph viewer`_

``*/test/``                        many directories have a test subdirectory containing test 
                                   modules (see `Testing in PyPy`_) 

``_cache/``                        holds cache files from internally `translating application 
                                   level to interpreterlevel`_ code.   
================================   =========================================== 

.. _`bytecode interpreter`: interpreter.html
.. _`translating application level to interpreterlevel`: geninterp.html
.. _`Testing in PyPy`: coding-guide.html#testing-in-pypy 
.. _`mixed modules`: coding-guide.html#mixed-modules 
.. _`modules`: coding-guide.html#modules 
.. _`basil`: http://people.cs.uchicago.edu/~jriehl/BasilTalk.pdf
.. _`object space`: objspace.html
.. _FlowObjSpace: objspace.html#the-flow-object-space 
.. _`trace object space`: objspace.html#the-trace-object-space 
.. _`taint object space`: objspace-proxies.html#taint
.. _`thunk object space`: objspace-proxies.html#thunk
.. _`transparent proxies`: objspace-proxies.html#tproxy
.. _`Differences between PyPy and CPython`: cpython_differences.html
.. _`What PyPy can do for your objects`: objspace-proxies.html
.. _`Stackless and coroutines`: stackless.html
.. _StdObjSpace: objspace.html#the-standard-object-space 
.. _`abstract interpretation`: http://en.wikipedia.org/wiki/Abstract_interpretation
.. _`rpython`: coding-guide.html#rpython 
.. _`type inferencing code`: translation.html#the-annotation-pass 
.. _`RPython Typer`: translation.html#rpython-typer 
.. _`testing methods`: coding-guide.html#testing-in-pypy
.. _`translation`: translation.html 
.. _`GenC backend`: translation.html#genc 
.. _`CLI backend`: cli-backend.html
.. _`py.py`: getting-started-python.html#the-py.py-interpreter
.. _`translatorshell.py`: getting-started-dev.html#try-out-the-translator
.. _JIT: jit/index.html
.. _`JIT Generation in PyPy`: jit/index.html
.. _`just-in-time compiler generator`: jit/index.html
.. _rtyper: rtyper.html
.. _`low-level type system`: rtyper.html#low-level-type
.. _`object-oriented type system`: rtyper.html#oo-type
.. _`garbage collector`: garbage_collection.html
.. _`Stackless Transform`: translation.html#the-stackless-transform
.. _`main PyPy-translation scripts`: getting-started-python.html#translating-the-pypy-python-interpreter
.. _`.NET`: http://www.microsoft.com/net/
.. _Mono: http://www.mono-project.com/
.. _`"standard library"`: rlib.html
.. _`graph viewer`: getting-started-dev.html#try-out-the-translator
.. _`compatibility matrix`: image/compat-matrix.png

.. include:: _ref.txt
