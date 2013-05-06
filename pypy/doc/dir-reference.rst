PyPy directory cross-reference 
------------------------------

Here is a fully referenced alphabetical two-level deep 
directory overview of PyPy: 

========================================  ============================================
Directory                                 explanation/links
========================================  ============================================
:source:`pypy/bin/`                       command-line scripts, mainly
                                          :source:`pypy/bin/pyinteractive.py`

:source:`pypy/config/`                    handles the numerous options for building
                                          and running PyPy

:source:`pypy/doc/`                       text versions of PyPy developer
                                          documentation

:source:`pypy/doc/config/`                documentation for the numerous translation
                                          options

:source:`pypy/doc/discussion/`            drafts of ideas and documentation

``doc/*/``                                other specific documentation topics or tools

:source:`pypy/interpreter/`               `bytecode interpreter`_ and related objects
                                          (frames, functions, modules,...) 

:source:`pypy/interpreter/pyparser/`      interpreter-level Python source parser

:source:`pypy/interpreter/astcompiler/`   interpreter-level bytecode compiler,
                                          via an AST representation

:source:`pypy/module/`                    contains `mixed modules`_
                                          implementing core modules with 
                                          both application and interpreter level code.
                                          Not all are finished and working.  Use
                                          the ``--withmod-xxx``
                                          or ``--allworkingmodules`` translation
                                          options.

:source:`pypy/objspace/`                  `object space`_ implementations

:source:`pypy/objspace/std/`              the StdObjSpace_ implementing CPython's
                                          objects and types

:source:`pypy/tool/`                      various utilities and hacks used
                                          from various places 

:source:`pypy/tool/algo/`                 general-purpose algorithmic and mathematic
                                          tools

:source:`pypy/tool/pytest/`               support code for our `testing methods`_


:source:`rpython/annotator/`              `type inferencing code`_ for
                                          `RPython`_ programs 

:source:`rpython/config/`                 handles the numerous options for RPython


:source:`rpython/flowspace/`              the FlowObjSpace_ implementing
                                          `abstract interpretation`_

:source:`rpython/rlib/`                   a `"standard library"`_ for RPython_
                                          programs

:source:`rpython/rtyper/`                 the `RPython Typer`_ 

:source:`rpython/rtyper/lltypesystem/`    the `low-level type system`_ for
                                          C-like backends

:source:`rpython/rtyper/ootypesystem/`    the `object-oriented type system`_
                                          for OO backends

:source:`rpython/memory/`                 the `garbage collector`_ construction
                                          framework

:source:`rpython/translator/`             translation_ backends and support code

:source:`rpython/translator/backendopt/`  general optimizations that run before a 
                                          backend generates code

:source:`rpython/translator/c/`           the `GenC backend`_, producing C code
                                          from an
                                          RPython program (generally via the rtyper_)

:source:`rpython/translator/cli/`         the `CLI backend`_ for `.NET`_
                                          (Microsoft CLR or Mono_)

:source:`pypy/goal/`                      our `main PyPy-translation scripts`_
                                          live here

:source:`rpython/translator/jvm/`         the Java backend

:source:`rpython/translator/tool/`        helper tools for translation

:source:`dotviewer/`                      `graph viewer`_

``*/test/``                               many directories have a test subdirectory
                                          containing test 
                                          modules (see `Testing in PyPy`_) 

``_cache/``                               holds cache files from various purposes
========================================  ============================================

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
.. _`main PyPy-translation scripts`: getting-started-python.html#translating-the-pypy-python-interpreter
.. _`.NET`: http://www.microsoft.com/net/
.. _Mono: http://www.mono-project.com/
.. _`"standard library"`: rlib.html
.. _`graph viewer`: getting-started-dev.html#try-out-the-translator
