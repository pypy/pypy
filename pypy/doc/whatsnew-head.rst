=======================
What's new in PyPy 2.5+
=======================

.. this is a revision shortly after release-2.4.x
.. startrev: 7026746cbb1b

.. branch: win32-fixes5

Fix c code generation for msvc so empty "{ }" are avoided in unions,
Avoid re-opening files created with NamedTemporaryFile,
Allocate by 4-byte chunks in rffi_platform,
Skip testing objdump if it does not exist,
and other small adjustments in own tests

.. branch: rtyper-stuff

Small internal refactorings in the rtyper.

.. branch: var-in-Some

Store annotations on the Variable objects, rather than in a big dict.
Introduce a new framework for double-dispatched annotation implementations.

.. branch: ClassRepr

Refactor ClassRepr and make normalizecalls independent of the rtyper.

.. branch: remove-remaining-smm

Remove all remaining multimethods.

.. branch: improve-docs

Split RPython documentation from PyPy documentation and clean up.  There now is
a clearer separation between documentation for users, developers and people
interested in background information.

.. branch: kill-multimethod

Kill multimethod machinery, all multimethods were removed earlier.

.. branch nditer-external_loop

Implement `external_loop` arguement to numpy's nditer

.. branch kill-rctime

Rename pypy/module/rctime to pypy/module/time, since it contains the implementation of the 'time' module.

.. branch: ssa-flow

Use SSA form for flow graphs inside build_flow() and part of simplify_graph()

.. branch: ufuncapi

Implement most of the GenericUfunc api to support numpy linalg. The strategy is
to encourage use of pure python or cffi ufuncs by extending frompyfunc().
See the docstring of frompyfunc for more details. This dovetails with a branch
of pypy/numpy - cffi-linalg which is a rewrite of the _umath_linalg module in
python, calling lapack from cffi. The branch also support traditional use of
cpyext GenericUfunc definitions in c.

.. branch: all_ordered_dicts
.. branch: berkerpeksag/fix-broken-link-in-readmerst-1415127402066
.. branch: bigint-with-int-ops
.. branch: dstufft/update-pip-bootstrap-location-to-the-new-1420760611527
.. branch: float-opt
.. branch: gc-incminimark-pinning
.. branch: gc_no_cleanup_nursery
.. branch: improve-gc-tracing-hooks
.. branch: improve-ptr-conv-error
.. branch: intern-not-immortal
.. branch: issue1922-take2
.. branch: kill-exported-symbols-list
.. branch: kill-rctime
.. branch: kill_ll_termios
.. branch: look-into-all-modules
.. branch: nditer-external_loop
.. branch: numpy-generic-item
.. branch: osx-shared
.. branch: portable-threadlocal
.. branch: pypy-dont-copy-ops
.. branch: recursion_and_inlining
.. branch: slim-down-resumedescr
.. branch: squeaky/use-cflags-for-compiling-asm
.. branch: unicode-fix
.. branch: zlib_zdict
