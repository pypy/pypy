PyPy directory cross-reference
------------------------------

Here is a fully referenced alphabetical two-level deep
directory overview of PyPy:

=================================  ============================================
Directory                          explanation/links
=================================  ============================================
`pypy/bin/`_                       command-line scripts, mainly
                                   `pypy/bin/pyinteractive.py`_

`pypy/config/`_                    handles the numerous options for building
                                   and running PyPy

`pypy/doc/`_                       text versions of PyPy developer
                                   documentation

`pypy/doc/config/`_                documentation for the numerous translation
                                   options

`pypy/doc/discussion/`_            drafts of ideas and documentation

``doc/*/``                         other specific documentation topics or tools

`pypy/interpreter/`_               `bytecode interpreter`_ and related objects
                                   (frames, functions, modules,...)

`pypy/interpreter/pyparser/`_      interpreter-level Python source parser

`pypy/interpreter/astcompiler/`_   interpreter-level bytecode compiler,
                                   via an AST representation

`pypy/module/`_                    contains `mixed modules`_
                                   implementing core modules with
                                   both application and interpreter level code.
                                   Not all are finished and working.  Use
                                   the ``--withmod-xxx``
                                   or ``--allworkingmodules`` translation
                                   options.

`pypy/objspace/`_                  `object space`_ implementations

`pypy/objspace/std/`_              the StdObjSpace_ implementing CPython's
                                   objects and types

`pypy/tool/`_                      various utilities and hacks used
                                   from various places

`pypy/tool/algo/`_                 general-purpose algorithmic and mathematic
                                   tools

`pypy/tool/pytest/`_               support code for our `testing methods`_


`rpython/annotator/`_              `type inferencing code`_ for
                                   `RPython`_ programs

`rpython/config/`_                 handles the numerous options for RPython


`rpython/flowspace/`_              the FlowObjSpace_ implementing
                                   `abstract interpretation`_

`rpython/rlib/`_                   a `"standard library"`_ for RPython_
                                   programs

`rpython/rtyper/`_                 the `RPython Typer`_

`rpython/rtyper/lltypesystem/`_    the `low-level type system`_ for
                                   C-like backends

`rpython/memory/`_                 the `garbage collector`_ construction
                                   framework

`rpython/translator/`_             translation_ backends and support code

`rpython/translator/backendopt/`_  general optimizations that run before a
                                   backend generates code

`rpython/translator/c/`_           the `GenC backend`_, producing C code
                                   from an
                                   RPython program (generally via the rtyper_)

`pypy/goal/`_                      our `main PyPy-translation scripts`_
                                   live here

`rpython/translator/tool/`_        helper tools for translation

`dotviewer/`_                      `graph viewer`_

``*/test/``                        many directories have a test subdirectory
                                   containing test
                                   modules (see `Testing in PyPy`_)

``_cache/``                        holds cache files from various purposes
=================================  ============================================

.. _`bytecode interpreter`: interpreter.html
.. _`Testing in PyPy`: coding-guide.html#testing-in-pypy
.. _`mixed modules`: coding-guide.html#mixed-modules
.. _`modules`: coding-guide.html#modules
.. _`basil`: http://people.cs.uchicago.edu/~jriehl/BasilTalk.pdf
.. _`object space`: objspace.html
.. _FlowObjSpace: objspace.html#the-flow-object-space
.. _`transparent proxies`: objspace-proxies.html#tproxy
.. _`Differences between PyPy and CPython`: cpython_differences.html
.. _`What PyPy can do for your objects`: objspace-proxies.html
.. _`Continulets and greenlets`: stackless.html
.. _StdObjSpace: objspace.html#the-standard-object-space
.. _`abstract interpretation`: http://en.wikipedia.org/wiki/Abstract_interpretation
.. _`rpython`: coding-guide.html#rpython
.. _`type inferencing code`: translation.html#the-annotation-pass
.. _`RPython Typer`: translation.html#rpython-typer
.. _`testing methods`: coding-guide.html#testing-in-pypy
.. _`translation`: translation.html
.. _`GenC backend`: translation.html#genc
.. _`py.py`: getting-started-python.html#the-py.py-interpreter
.. _`translatorshell.py`: getting-started-dev.html#try-out-the-translator
.. _JIT: jit/index.html
.. _`JIT Generation in PyPy`: jit/index.html
.. _`just-in-time compiler generator`: jit/index.html
.. _rtyper: rtyper.html
.. _`low-level type system`: rtyper.html#low-level-type
.. _`object-oriented type system`: rtyper.html#oo-type
.. _`garbage collector`: garbage_collection.html
.. _`main PyPy-translation scripts`: getting-started-python.html#translating-the-pypy-python-interpreter
.. _`.NET`: http://www.microsoft.com/net/
.. _Mono: http://www.mono-project.com/
.. _`"standard library"`: rlib.html
.. _`graph viewer`: getting-started-dev.html#try-out-the-translator
